import requests
import json
import flask
import os
import secrets
import csv
import io
from datetime import datetime

app = flask.Flask(__name__)

# Load or generate a persistent SECRET_KEY
SECRET_KEY_FILE = 'secret_key.txt'

def get_secret_key():
    """Load secret key from file, or generate and save a new one if it doesn't exist."""
    # First priority: environment variable (for production with external secret management)
    if os.environ.get('SECRET_KEY'):
        return os.environ.get('SECRET_KEY')
    
    # Second priority: load from file (for persistence across restarts)
    if os.path.exists(SECRET_KEY_FILE):
        try:
            with open(SECRET_KEY_FILE, 'r') as f:
                return f.read().strip()
        except Exception as e:
            print(f"Warning: Could not read secret key file: {e}")
    
    # Last resort: generate a new key and save it
    new_key = secrets.token_hex(32)
    try:
        # Create file with restricted permissions (owner read/write only)
        # Using os.open with specific flags for secure file creation
        fd = os.open(SECRET_KEY_FILE, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(new_key)
        print(f"Generated new secret key and saved to {SECRET_KEY_FILE}")
    except FileExistsError:
        # File was created between the exists check and open - try reading it
        with open(SECRET_KEY_FILE, 'r') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Warning: Could not save secret key to file: {e}")
    
    return new_key

app.secret_key = get_secret_key()

# Additional security configurations for sessions
app.config.update(
    SESSION_COOKIE_SECURE=os.environ.get('HTTPS_ENABLED', 'false').lower() == 'true',
    SESSION_COOKIE_HTTPONLY=True,  # Prevent JavaScript access to session cookie
    SESSION_COOKIE_SAMESITE='Lax'  # CSRF protection
)

@app.route('/manifest.json')
def manifest():
    return flask.send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    return flask.send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/')
def home():
    return flask.render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login_route():
    # Redirect GET requests to home page
    if flask.request.method == 'GET':
        return flask.redirect('/')
    
    user_id = flask.request.form['user_id']
    user_pass = flask.request.form['user_pass']
    
    try:
        login_response = login(user_id, user_pass)
        token = login_response["token"]
        if token is None or token == "":
            return flask.render_template('login.html', error="Token non valido. Riprova.")
        
        # Store token and user_id in session
        flask.session['token'] = token
        flask.session['user_id'] = user_id
        
        student_id = "".join(filter(str.isdigit, user_id))
        grades_avr = calculate_avr(get_grades(student_id, token))
        
        # Store grades in session for other pages
        flask.session['grades_avr'] = grades_avr
        
        # Redirect to grades page instead of rendering template
        return flask.redirect('/grades')
    except requests.exceptions.HTTPError as e:
        # Handle 422 and other HTTP errors with user-friendly message
        if e.response.status_code == 422:
            return flask.render_template('login.html', error="Credenziali non valide. Verifica User ID e Password.")
        else:
            return flask.render_template('login.html', error=f"Errore di autenticazione ({e.response.status_code}). Riprova.")
    except requests.exceptions.RequestException as e:
        return flask.render_template('login.html', error="Errore di connessione. Verifica la tua connessione internet.")
    except Exception as e:
        return flask.render_template('login.html', error="Errore imprevisto. Riprova più tardi.")

@app.route('/logout', methods=['POST'])
def logout():
    flask.session.clear()
    return flask.redirect('/')

@app.route('/refresh_grades', methods=['POST'])
def refresh_grades():
    """Refresh grades from ClasseViva API"""
    if 'token' not in flask.session:
        return flask.jsonify({'error': 'No active session'}), 401
    
    try:
        token = flask.session['token']
        # Extract student_id from session or regenerate from stored user_id
        # We need to store user_id during login to use it here
        if 'user_id' not in flask.session:
            return flask.jsonify({'error': 'User ID not found in session'}), 400
        
        user_id = flask.session['user_id']
        student_id = "".join(filter(str.isdigit, user_id))
        
        # Fetch fresh grades from API
        grades_avr = calculate_avr(get_grades(student_id, token))
        
        # Update session with fresh data
        flask.session['grades_avr'] = grades_avr
        
        return flask.jsonify({'success': True, 'message': 'Voti aggiornati'}), 200
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            # Token expired, redirect to login
            flask.session.clear()
            return flask.jsonify({'error': 'Sessione scaduta', 'redirect': '/'}), 401
        return flask.jsonify({'error': f'Errore durante l\'aggiornamento: {e.response.status_code}'}), 500
    except Exception as e:
        return flask.jsonify({'error': 'Errore durante l\'aggiornamento dei voti'}), 500

@app.route('/grades')
def grades_page():
    """Display grades page - requires active session with token"""
    if 'grades_avr' not in flask.session:
        return flask.redirect('/')
    
    grades_avr = flask.session['grades_avr']
    return flask.render_template('grades.html', grades_avr=grades_avr)

@app.route('/charts')
def charts_page():
    """Display charts page - requires active session with grades data"""
    if 'grades_avr' not in flask.session:
        return flask.redirect('/')
    
    grades_avr = flask.session['grades_avr']
    return flask.render_template('charts.html', grades_avr=grades_avr)

@app.route('/export')
def export_page():
    """Display export page - requires active session"""
    if 'token' not in flask.session:
        return flask.redirect('/')
    
    return flask.render_template('export.html')

@app.route('/info')
def info_page():
    """Display info page"""
    return flask.render_template('info.html')

@app.route('/export/csv', methods=['POST'])
def export_csv():
    """Export grades as CSV file"""
    if 'grades_avr' not in flask.session:
        return flask.redirect('/')
    
    grades_avr = flask.session['grades_avr']
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Periodo', 'Materia', 'Voto', 'Data', 'Tipo', 'Docente', 'Note'])
    
    # Write data
    for period in sorted(grades_avr.keys()):
        if period == 'all_avr':
            continue
        
        for subject, data in grades_avr[period].items():
            if subject == 'period_avr':
                continue
            
            for grade in data.get('grades', []):
                writer.writerow([
                    f'Periodo {period}',
                    subject,
                    grade.get('decimalValue', ''),
                    grade.get('evtDate', ''),
                    grade.get('componentDesc', ''),
                    grade.get('teacherName', ''),
                    grade.get('notesForFamily', '')
                ])
    
    # Prepare response
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    response = flask.Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename=voti_{timestamp}.csv'
    
    return response

def login(user_id, user_pass):
    url = "https://web.spaggiari.eu/rest/v1/auth/login"
    headers = {
        "Content-Type": "application/json",
        "Z-Dev-ApiKey": "Tg1NWEwNGIgIC0K",
        "User-Agent": "CVVS/std/4.1.7 Android/10"
    }
    body = {
        "ident": None,
        "pass": user_pass,
        "uid": user_id
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(body))
    
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def get_periods(student_id, token):
    url = f"https://web.spaggiari.eu/rest/v1/students/{student_id}/periods"
    headers = {
        "Content-Type": "application/json",
        "Z-Dev-ApiKey": "Tg1NWEwNGIgIC0K",
        "User-Agent": "CVVS/std/4.1.7 Android/10",
        "Z-Auth-Token": token
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def get_grades(student_id, token):
    url = f"https://web.spaggiari.eu/rest/v1/students/{student_id}/grades"
    headers = {
        "Content-Type": "application/json",
        "Z-Dev-ApiKey": "Tg1NWEwNGIgIC0K",
        "User-Agent": "CVVS/std/4.1.7 Android/10",
        "Z-Auth-Token": token
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        # print(json.dumps(response.json(), indent=4))
        return response.json()
    else:
        response.raise_for_status()
def calculate_avr(grades):
    grades_avr = {}
    for grade in grades["grades"]:
        # Convert period to string to ensure consistent type for dictionary keys
        period = str(grade["periodPos"])
        if grade["noAverage"] is True or grade["color"] == "blue" or grade["decimalValue"] is None:
            continue
        if period not in grades_avr:
            grades_avr[period] = {}
        if grades_avr[period].get(grade["subjectDesc"]) is None:
            grades_avr[period][grade["subjectDesc"]] = {"count": 0, "avr": 0, "grades": []}
        
        grades_avr[period][grade["subjectDesc"]]["count"] += 1
        
        # Append grade as a dictionary with additional fields
        grades_avr[period][grade["subjectDesc"]]["grades"].append({
            "decimalValue": grade["decimalValue"],
            "evtDate": grade["evtDate"],
            "notesForFamily": grade["notesForFamily"],
            "componentDesc": grade["componentDesc"],
            "teacherName": grade["teacherName"]
        })
    
    # Calculate average per subject
    for period in grades_avr:
        for subject in grades_avr[period]:
            subject_grades = [g['decimalValue'] for g in grades_avr[period][subject]['grades']]
            grades_avr[period][subject]["avr"] = sum(subject_grades) / len(subject_grades) if subject_grades else 0
    
    # Calculate period averages
    for period in grades_avr:
        period_grades = []
        for subject in grades_avr[period]:
            period_grades.extend([g['decimalValue'] for g in grades_avr[period][subject]['grades']])
        grades_avr[period]["period_avr"] = sum(period_grades) / len(period_grades) if period_grades else 0
    
    # Calculate overall average
    grades_avr["all_avr"] = sum([grades_avr[period]["period_avr"] for period in grades_avr]) / len(grades_avr) if grades_avr else 0
    
    # print(json.dumps(grades_avr, indent=4))
    return grades_avr
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
    # app.run(debug=True)

