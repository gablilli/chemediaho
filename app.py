import requests
import json
import flask
import os
import secrets

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
        
        # Store token in session for the grades page
        flask.session['token'] = token
        
        student_id = "".join(filter(str.isdigit, user_id))
        grades_avr = calculate_avr(get_grades(student_id, token))
        return flask.render_template('grades.html', grades_avr=grades_avr)
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
        period = grade["periodPos"]
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

