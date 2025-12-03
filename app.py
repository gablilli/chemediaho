import requests
import json
import flask
import os
import secrets
import csv
import io
from datetime import datetime
from bs4 import BeautifulSoup
import re
import logging

app = flask.Flask(__name__)

# Application version
APP_VERSION = "1.6.6"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mark conversion table (from ClasseViva)
MARK_TABLE = {
    "1": 1, "1+": 1.25, "1½": 1.5, "2-": 1.75, "2": 2, "2+": 2.25, "2½": 2.5,
    "3-": 2.75, "3": 3, "3+": 3.25, "3½": 3.5, "4-": 3.75, "4": 4, "4+": 4.25,
    "4½": 4.5, "5-": 4.75, "5": 5, "5+": 5.25, "5½": 5.5, "6-": 5.75, "6": 6,
    "6+": 6.25, "6½": 6.5, "7-": 6.75, "7": 7, "7+": 7.25, "7½": 7.5, "8-": 7.75,
    "8": 8, "8+": 8.25, "8½": 8.5, "9-": 8.75, "9": 9, "9+": 9.25, "9½": 9.5,
    "10-": 9.75, "10": 10
}

# Religion grades (these don't count towards average)
RELIGION_GRADES = {
    "o": 10, "ottimo": 10,
    "ds": 9, "distinto": 9,
    "b": 8, "buono": 8,
    "d": 7, "discreto": 7,
    "s": 6, "sufficiente": 6,
    "ins": 5, "insufficiente": 5, "non sufficiente": 5
}

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
        
        # Default preference is to exclude blue grades (False)
        if 'include_blue_grades' not in flask.session:
            flask.session['include_blue_grades'] = False
        
        # Use web scraping to get grades (includes proper blue grade detection)
        include_blue_grades = flask.session.get('include_blue_grades', False)
        grades_avr = calculate_avr(get_grades_web(token, user_id), include_blue_grades)
        
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
        
        # Get preference for including blue grades (default is False)
        include_blue_grades = flask.session.get('include_blue_grades', False)
        
        # Use web scraping to get grades (includes proper blue grade detection)
        grades_avr = calculate_avr(get_grades_web(token, user_id), include_blue_grades)
        
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

@app.route('/update_blue_grades_preference', methods=['POST'])
def update_blue_grades_preference():
    """Update preference for including blue grades in averages"""
    if 'token' not in flask.session:
        return flask.jsonify({'error': 'No active session'}), 401
    
    try:
        data = flask.request.get_json()
        include_blue_grades = data.get('includeBlueGrades', False)
        
        # Store preference in session
        flask.session['include_blue_grades'] = include_blue_grades
        
        # Recalculate averages with new preference
        token = flask.session['token']
        user_id = flask.session['user_id']
        
        # Use web scraping to get grades (includes proper blue grade detection)
        grades_avr = calculate_avr(get_grades_web(token, user_id), include_blue_grades)
        
        # Update session with recalculated data
        flask.session['grades_avr'] = grades_avr
        
        return flask.jsonify({'success': True, 'message': 'Preferenza aggiornata'}), 200
    except Exception as e:
        logger.error(f"Error updating blue grades preference: {e}")
        return flask.jsonify({'error': 'Errore durante l\'aggiornamento della preferenza'}), 500

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

@app.route('/settings')
def settings_page():
    """Display settings page"""
    return flask.render_template('settings.html', version=APP_VERSION)

@app.route('/goal')
def goal_page():
    """Display goal calculator page - requires active session"""
    if 'grades_avr' not in flask.session:
        return flask.redirect('/')
    
    grades_avr = flask.session['grades_avr']
    return flask.render_template('goal.html', grades_avr=grades_avr)

@app.route('/calculate_goal', methods=['POST'])
def calculate_goal():
    """Calculate what grade is needed to reach a target average"""
    if 'grades_avr' not in flask.session:
        return flask.jsonify({'error': 'No active session'}), 401
    
    try:
        data = flask.request.get_json()
        period = data.get('period')
        subject = data.get('subject')
        target_average = float(data.get('target_average'))
        num_grades = int(data.get('num_grades', 1))  # Number of grades to calculate for
        
        grades_avr = flask.session['grades_avr']
        
        # Validate inputs
        if period not in grades_avr or subject not in grades_avr[period]:
            return flask.jsonify({'error': 'Materia o periodo non trovato'}), 400
        
        if target_average < 1 or target_average > 10:
            return flask.jsonify({'error': 'La media target deve essere tra 1 e 10'}), 400
        
        if num_grades < 1 or num_grades > 10:
            return flask.jsonify({'error': 'Il numero di voti deve essere tra 1 e 10'}), 400
        
        # Get current grades with validation
        subject_data = grades_avr[period][subject]
        if 'grades' not in subject_data or not isinstance(subject_data['grades'], list):
            return flask.jsonify({'error': 'Dati dei voti non validi'}), 400
        
        # Get preference for including blue grades
        include_blue_grades = flask.session.get('include_blue_grades', False)
        
        # Extract grades with validation (respecting blue grades preference)
        current_grades = []
        for g in subject_data['grades']:
            if isinstance(g, dict) and 'decimalValue' in g and g['decimalValue'] is not None:
                # Include grade if: not blue, OR (blue AND preference is to include blue)
                if not g.get('isBlue', False) or include_blue_grades:
                    current_grades.append(g['decimalValue'])
        
        if not current_grades:
            return flask.jsonify({'error': 'Nessun voto disponibile per questa materia'}), 400
        
        current_count = len(current_grades)
        current_sum = sum(current_grades)
        current_average = subject_data.get('avr', current_sum / current_count if current_count > 0 else 0)
        
        # Validate that target average is not below current average
        if target_average < current_average:
            return flask.jsonify({'error': f'La media target ({target_average}) non può essere inferiore alla media attuale ({round(current_average, 2)}).'}), 400
        
        # Calculate required grades
        # For multiple grades, we calculate the average grade needed
        # Formula: (current_sum + required_sum) / (current_count + num_grades) = target_average
        # required_sum = target_average * (current_count + num_grades) - current_sum
        required_sum = target_average * (current_count + num_grades) - current_sum
        required_average_grade = required_sum / num_grades
        
        # Round grades >= 9.75 to 10 for display purposes
        display_grade = required_average_grade
        if 9.75 <= required_average_grade <= 10:
            display_grade = 10
        
        # Note: For simplicity and clarity, we assume all required grades are the same
        # This gives the student a single, clear target to aim for across all tests
        required_grades = [display_grade] * num_grades
        
        # Determine if it's achievable (use original value for comparison, but allow 9.75+ to round to 10)
        achievable = 1 <= required_average_grade <= 10
        
        return flask.jsonify({
            'success': True,
            'current_average': round(current_average, 2),
            'target_average': target_average,
            'required_grade': round(display_grade, 2),
            'required_grades': [round(g, 2) for g in required_grades],
            'current_grades_count': current_count,
            'achievable': achievable,
            'message': get_goal_message_multiple(required_average_grade, display_grade, target_average, current_average, num_grades)
        }), 200
        
    except ValueError as e:
        return flask.jsonify({'error': 'Valori non validi'}), 400
    except Exception as e:
        return flask.jsonify({'error': 'Errore durante il calcolo'}), 500

def get_goal_message_multiple(raw_grade, display_grade, target_average, current_average, num_grades):
    """Generate a helpful message based on the calculation result for multiple grades"""
    grade_text = "voto" if num_grades == 1 else f"{num_grades} voti"
    
    if raw_grade < 1:
        return f"Ottimo! La tua media attuale è già sopra l'obiettivo. Anche con voti minimi raggiungerai {target_average}."
    elif raw_grade > 10:
        return f"Purtroppo non è possibile raggiungere {target_average} con {grade_text}. Prova a impostare un obiettivo più realistico o aggiungere più voti!"
    elif 9.75 <= raw_grade <= 10:
        return f"Ci vuole impegno! Ti servono {grade_text} da 10 (arrotondato da {round(raw_grade, 2)}) per raggiungere l'obiettivo."
    elif raw_grade >= 9:
        return f"Devi impegnarti molto: ti servono {grade_text} da almeno {round(raw_grade, 1)} per raggiungere l'obiettivo."
    elif raw_grade >= 7:
        return f"È fattibile: Con {grade_text} da {round(raw_grade, 1)} puoi raggiungere {target_average}."
    elif raw_grade >= 6:
        return f"Ci sei quasi! {grade_text.capitalize()} da {round(raw_grade, 1)} ti permetteranno di raggiungere l'obiettivo."
    else:
        return f"Ottimo! Anche con {grade_text} modesti ({round(raw_grade, 1)}) raggiungerai {target_average}."

@app.route('/predict_average', methods=['POST'])
def predict_average():
    """Predict how hypothetical grades will affect the average"""
    if 'grades_avr' not in flask.session:
        return flask.jsonify({'error': 'No active session'}), 401
    
    try:
        data = flask.request.get_json()
        period = data.get('period')
        subject = data.get('subject')
        predicted_grades = data.get('predicted_grades', [])
        
        grades_avr = flask.session['grades_avr']
        
        # Validate inputs
        if period not in grades_avr or subject not in grades_avr[period]:
            return flask.jsonify({'error': 'Materia o periodo non trovato'}), 400
        
        if not predicted_grades or not isinstance(predicted_grades, list):
            return flask.jsonify({'error': 'Inserisci almeno un voto previsto'}), 400
        
        # Validate predicted grades
        for grade in predicted_grades:
            if not isinstance(grade, (int, float)) or grade < 1 or grade > 10:
                return flask.jsonify({'error': 'Tutti i voti devono essere tra 1 e 10'}), 400
        
        # Get current grades with validation
        subject_data = grades_avr[period][subject]
        if 'grades' not in subject_data or not isinstance(subject_data['grades'], list):
            return flask.jsonify({'error': 'Dati dei voti non validi'}), 400
        
        # Get preference for including blue grades
        include_blue_grades = flask.session.get('include_blue_grades', False)
        
        # Extract current grades (respecting blue grades preference)
        current_grades = []
        for g in subject_data['grades']:
            if isinstance(g, dict) and 'decimalValue' in g and g['decimalValue'] is not None:
                # Include grade if: not blue, OR (blue AND preference is to include blue)
                if not g.get('isBlue', False) or include_blue_grades:
                    current_grades.append(g['decimalValue'])
        
        if not current_grades:
            return flask.jsonify({'error': 'Nessun voto disponibile per questa materia'}), 400
        
        current_average = subject_data.get('avr', sum(current_grades) / len(current_grades))
        
        # Calculate predicted average
        all_grades = current_grades + predicted_grades
        predicted_average = sum(all_grades) / len(all_grades)
        
        # Calculate change
        change = predicted_average - current_average
        
        # Generate message
        message = get_predict_message(change, predicted_average, len(predicted_grades))
        
        return flask.jsonify({
            'success': True,
            'current_average': round(current_average, 2),
            'predicted_average': round(predicted_average, 2),
            'change': round(change, 2),
            'num_predicted_grades': len(predicted_grades),
            'message': message
        }), 200
        
    except ValueError as e:
        return flask.jsonify({'error': 'Valori non validi'}), 400
    except Exception as e:
        return flask.jsonify({'error': 'Errore durante il calcolo'}), 500

def get_predict_message(change, predicted_average, num_grades):
    """Generate a helpful message based on the prediction result"""
    grade_text = "voto" if num_grades == 1 else f"{num_grades} voti"
    
    if change > 0.5:
        return f"Ottimo! Con {grade_text} la tua media salirebbe a {round(predicted_average, 2)} ({change:+.2f})! 📈"
    elif change > 0:
        return f"Bene! Con {grade_text} la tua media migliorerebbe leggermente a {round(predicted_average, 2)} ({change:+.2f}). ✅"
    elif change == 0:
        return f"Con {grade_text} la tua media rimarrebbe stabile a {round(predicted_average, 2)}. ➡️"
    elif change > -0.5:
        return f"Attenzione! Con {grade_text} la tua media scenderebbe leggermente a {round(predicted_average, 2)} ({change:.2f}). ⚠️"
    else:
        return f"Attenzione! Con {grade_text} la tua media scenderebbe significativamente a {round(predicted_average, 2)} ({change:.2f}). 📉"

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

def get_periods_web(token, user_id):
    """Get periods by scraping the web page"""
    # Extract numeric student ID from user_id
    student_id = "".join(filter(str.isdigit, user_id))
    
    url = "https://web.spaggiari.eu/cvv/app/default/genitori_voti.php"
    headers = {
        "Cookie": f"PHPSESSID={token}; webidentity={student_id};",
        "User-Agent": "Mozilla/5.0"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        periods = []
        
        # Find the periods list (first ul element)
        periods_container = soup.find('ul')
        if periods_container:
            for i, period_li in enumerate(periods_container.find_all('li', recursive=False)):
                link = period_li.find('a')
                if link and 'href' in link.attrs:
                    period_code = link['href'].split('#')[1] if '#' in link['href'] else ""
                    period_text = period_li.get_text(strip=True)
                    # Clean up period description (remove duplicate patterns like "1° 1° PERIODO" -> "1° PERIODO")
                    period_text = re.sub(r'(\d+°)\s+\1', r'\1', period_text)
                    
                    periods.append({
                        'periodCode': period_code,
                        'periodPos': i + 1,
                        'periodDesc': period_text
                    })
        
        return periods
    except Exception as e:
        logger.error(f"Error fetching periods from web: {e}")
        return []

def get_grades_web(token, user_id):
    """Get grades by scraping the web page instead of using REST API"""
    # Extract numeric student ID from user_id
    student_id = "".join(filter(str.isdigit, user_id))
    
    url = "https://web.spaggiari.eu/cvv/app/default/genitori_voti.php"
    headers = {
        "Cookie": f"PHPSESSID={token}; webidentity={student_id};",
        "User-Agent": "Mozilla/5.0"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get periods first
        periods = get_periods_web(token, user_id)
        if not periods:
            return {"grades": []}
        
        all_grades = []
        
        for period in periods:
            # Find the table for this period
            period_table = soup.find('table', {'sessione': period['periodCode']})
            if not period_table:
                continue
            
            tbody = period_table.find('tbody')
            if not tbody:
                continue
            
            # Get subject IDs from riga_competenza_default rows
            subject_rows = tbody.find_all('tr', class_='riga_competenza_default')
            subject_ids = []
            for row in subject_rows:
                if len(row.find_all('td')) > 1:
                    materia_id = row.get('materia_id', '0')
                    subject_ids.append(materia_id)
            
            # Get grade rows
            grade_rows = tbody.find_all('tr', class_='riga_materia_componente')
            
            for subject_index, row in enumerate(grade_rows):
                cells = row.find_all('td')
                if len(cells) <= 1:
                    continue
                
                # First cell is subject name
                subject_name = cells[0].get_text(strip=True).upper()
                
                # Get subject ID safely
                subject_id = int(subject_ids[subject_index]) if subject_index < len(subject_ids) and subject_ids[subject_index].isdigit() else 0
                
                # Find grade cells (cells with class cella_voto)
                grade_cells = row.find_all('td', class_='cella_voto')
                
                for grade_cell in grade_cells:
                    # Find span elements within the grade cell
                    spans = grade_cell.find_all('span')
                    
                    if len(spans) < 2:
                        continue
                    
                    # First span is date, second is grade value
                    date_elem = spans[0]
                    grade_elem = spans[1]
                    
                    evt_date = date_elem.get_text(strip=True)
                    display_value = grade_elem.get_text(strip=True)
                    
                    if not display_value or display_value == '-':
                        continue
                    
                    # Check if it's a religion grade
                    is_religion = display_value.lower() in RELIGION_GRADES
                    
                    # Calculate decimal value
                    if is_religion:
                        decimal_value = RELIGION_GRADES.get(display_value.lower(), 0)
                    else:
                        decimal_value = MARK_TABLE.get(display_value, 0)
                    
                    # Check if grade is blue (non-counting)
                    # Blue grades have class f_reg_voto_dettaglio OR are religion grades
                    grade_classes = grade_elem.get('class') or []
                    has_blue_class = 'f_reg_voto_dettaglio' in grade_classes
                    color = "blue" if (has_blue_class or is_religion) else "green"
                    
                    # Get additional info
                    evt_id = grade_cell.get('evento_id', '0')
                    component_desc = grade_elem.get('title', '')
                    
                    all_grades.append({
                        'subjectId': subject_id,
                        'subjectDesc': subject_name,
                        'evtId': int(evt_id) if evt_id.isdigit() else 0,
                        'evtDate': evt_date,
                        'decimalValue': decimal_value if decimal_value > 0 else None,
                        'displayValue': display_value,
                        'color': color,
                        'periodPos': period['periodPos'],
                        'periodDesc': period['periodDesc'],
                        'componentDesc': component_desc,
                        'notesForFamily': '',  # Not available in main page, needs separate fetch
                        'teacherName': ''  # Not available in main page
                    })
        
        return {"grades": all_grades}
        
    except Exception as e:
        logger.error(f"Error fetching grades from web: {e}")
        return {"grades": []}

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
def calculate_avr(grades, include_blue_grades=False):
    """
    Calculate averages for grades
    
    Args:
        grades: Dictionary with 'grades' key containing list of grade objects
        include_blue_grades: If True, include blue grades in average calculations
    """
    grades_avr = {}
    for grade in grades["grades"]:
        # Convert period to string to ensure consistent type for dictionary keys
        period = str(grade["periodPos"])
        # Always skip grades without a decimal value
        if grade["decimalValue"] is None:
            continue
        # Take all grades from Spaggiari as-is without filtering
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
            "teacherName": grade["teacherName"],
            "isBlue": grade["color"] == "blue"
        })
    
    # Calculate average per subject
    for period in grades_avr:
        for subject in grades_avr[period]:
            if include_blue_grades:
                # Include all grades in average calculation
                subject_grades = [g['decimalValue'] for g in grades_avr[period][subject]['grades']]
            else:
                # Only include non-blue grades in average calculation
                subject_grades = [g['decimalValue'] for g in grades_avr[period][subject]['grades'] if not g.get('isBlue', False)]
            grades_avr[period][subject]["avr"] = sum(subject_grades) / len(subject_grades) if subject_grades else 0
    
    # Calculate period averages
    for period in grades_avr:
        period_grades = []
        for subject in grades_avr[period]:
            if include_blue_grades:
                # Include all grades in period average
                period_grades.extend([g['decimalValue'] for g in grades_avr[period][subject]['grades']])
            else:
                # Only include non-blue grades in period average
                period_grades.extend([g['decimalValue'] for g in grades_avr[period][subject]['grades'] if not g.get('isBlue', False)])
        grades_avr[period]["period_avr"] = sum(period_grades) / len(period_grades) if period_grades else 0
    
    # Calculate overall average
    grades_avr["all_avr"] = sum([grades_avr[period]["period_avr"] for period in grades_avr]) / len(grades_avr) if grades_avr else 0
    
    # print(json.dumps(grades_avr, indent=4))
    return grades_avr
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8001)
    # app.run(debug=True)

