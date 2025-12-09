import requests
import json
import flask
import os
import secrets
import csv
import io
import logging
from datetime import datetime

app = flask.Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Application version
APP_VERSION = "1.8.0"

# Constants for grade calculations
GRADE_ROUNDING_THRESHOLD = 9.5  # Grades >= 9.5 can be rounded to 10
DEFAULT_INCLUDE_BLUE_GRADES = False  # Default: don't include blue grades

# Constants for intelligent subject suggestions
# SUGGESTION_IMPACT_WEIGHT: Balances difficulty vs. impact in scoring
#   - Lower values (e.g., 0.05) prioritize subjects with lower current averages
#   - Higher values (e.g., 0.2) prioritize subjects with fewer grades (higher impact per grade)
#   - 0.1 provides a good balance between both factors
SUGGESTION_IMPACT_WEIGHT = 0.1
# MAX_SUGGESTIONS: Number of subject suggestions to return
#   - 5 provides enough variety without overwhelming the user
MAX_SUGGESTIONS = 5

# Allowed grade values for smart calculator
ALLOWED_GRADES = [4, 4.25, 4.5, 4.75, 5, 5.25, 5.5, 5.75, 6, 6.25, 6.5, 6.75, 7, 7.25, 7.5, 7.75, 8, 8.25, 8.5, 8.75, 9, 9.25, 9.5, 9.75, 10]

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
    manifest_data = {
        "name": "che media ho?",
        "short_name": "chemediaho?",
        "description": "Visualizza la media dei voti di ClasseViva",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#130909",
        "theme_color": "#c84444",
        "orientation": "portrait",
        "icons": [
            {
                "src": "/static/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/static/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    
    return flask.jsonify(manifest_data)

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
        
        # Fetch fresh grades from API - take all grades as-is without filtering
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

@app.route('/settings')
def settings_page():
    """Display settings page"""
    return flask.render_template('settings.html', version=APP_VERSION)

@app.route('/overall_average_detail')
def overall_average_detail_page():
    """Display overall average detail page with graphs and smart suggestions"""
    if 'grades_avr' not in flask.session:
        return flask.redirect('/')
    
    grades_avr = flask.session['grades_avr']
    return flask.render_template('overall_average_detail.html', grades_avr=grades_avr)

@app.route('/subject_detail/<subject_name>')
def subject_detail_page(subject_name):
    """Display subject detail page with graphs and smart suggestions"""
    if 'grades_avr' not in flask.session:
        return flask.redirect('/')
    
    grades_avr = flask.session['grades_avr']
    
    # Verify subject exists
    subject_found = False
    for period in grades_avr:
        if period != 'all_avr' and subject_name in grades_avr[period]:
            subject_found = True
            break
    
    if not subject_found:
        return flask.redirect('/grades')
    
    return flask.render_template('subject_detail.html', grades_avr=grades_avr, subject_name=subject_name)

@app.route('/goal')
def goal_page():
    """Display goal calculator page - requires active session"""
    if 'grades_avr' not in flask.session:
        return flask.redirect('/')
    
    grades_avr = flask.session['grades_avr']
    return flask.render_template('goal.html', grades_avr=grades_avr)

@app.route('/calculate_goal', methods=['POST'])
def calculate_goal():
    """Calculate what grade is needed to reach a target average in a specific period.
    If subject is not provided, returns intelligent suggestions for all subjects in the period."""
    if 'grades_avr' not in flask.session:
        return flask.jsonify({'error': 'No active session'}), 401
    
    try:
        data = flask.request.get_json()
        period = data.get('period')
        subject = data.get('subject')  # Optional now
        target_average = float(data.get('target_average'))
        num_grades = int(data.get('num_grades', 1))  # Number of grades to calculate for
        
        grades_avr = flask.session['grades_avr']
        
        # Validate inputs
        if not period or period not in grades_avr:
            return flask.jsonify({'error': 'Periodo non trovato'}), 400
        
        if target_average < 1 or target_average > 10:
            return flask.jsonify({'error': 'La media target deve essere tra 1 e 10'}), 400
        
        if num_grades < 1 or num_grades > 10:
            return flask.jsonify({'error': 'Il numero di voti deve essere tra 1 e 10'}), 400
        
        # If no subject specified, return intelligent suggestions for the period
        if not subject:
            suggestions = calculate_period_subject_suggestions(grades_avr, period, target_average, num_grades)
            
            return flask.jsonify({
                'success': True,
                'period': period,
                'target_average': target_average,
                'suggestions': suggestions,
                'num_grades': num_grades,
                'message': get_period_suggestion_message(suggestions, target_average, num_grades, period)
            }), 200
        
        # If subject is specified, calculate for that specific subject
        if subject not in grades_avr[period]:
            return flask.jsonify({'error': 'Materia non trovata nel periodo selezionato'}), 400
        
        # Get current grades with validation
        subject_data = grades_avr[period][subject]
        if 'grades' not in subject_data or not isinstance(subject_data['grades'], list):
            return flask.jsonify({'error': 'Dati dei voti non validi'}), 400
        
        # Extract grades with validation
        current_grades = []
        for g in subject_data['grades']:
            if isinstance(g, dict) and 'decimalValue' in g and g['decimalValue'] is not None:
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
        
        # Round to nearest allowed grade
        display_grade = round_to_allowed_grade(required_average_grade)
        
        # Note: For simplicity and clarity, we assume all required grades are the same
        # This gives the student a single, clear target to aim for across all tests
        required_grades = [display_grade] * num_grades
        
        # Determine if it's achievable (use original value for comparison)
        achievable = min(ALLOWED_GRADES) <= required_average_grade <= max(ALLOWED_GRADES)
        
        return flask.jsonify({
            'success': True,
            'current_average': round(current_average, 2),
            'target_average': target_average,
            'required_grade': display_grade,
            'required_grades': required_grades,
            'current_grades_count': current_count,
            'achievable': achievable,
            'subject': subject,
            'message': get_goal_message_multiple(required_average_grade, display_grade, target_average, current_average, num_grades)
        }), 200
        
    except ValueError as e:
        return flask.jsonify({'error': 'Valori non validi'}), 400
    except Exception as e:
        logger.error(f"Error calculating goal: {e}", exc_info=True)
        return flask.jsonify({'error': 'Errore durante il calcolo'}), 500

def round_to_allowed_grade(grade):
    """Round a grade to the nearest allowed value"""
    if grade < min(ALLOWED_GRADES):
        return min(ALLOWED_GRADES)
    if grade > max(ALLOWED_GRADES):
        return max(ALLOWED_GRADES)
    
    # Find the closest allowed grade
    closest = min(ALLOWED_GRADES, key=lambda x: abs(x - grade))
    return closest

def get_goal_message_multiple(raw_grade, display_grade, target_average, current_average, num_grades):
    """Generate a helpful message based on the calculation result for multiple grades"""
    grade_text = "un voto" if num_grades == 1 else f"{num_grades} voti"
    
    if raw_grade < 1:
        return f"Ottimo! La tua media attuale è già sopra l'obiettivo. Anche con voti minimi raggiungerai {target_average}."
    elif raw_grade > 10:
        return f"Purtroppo non è possibile raggiungere {target_average} con {grade_text}. Prova a impostare un obiettivo più realistico o aggiungere più voti!"
    elif GRADE_ROUNDING_THRESHOLD <= raw_grade <= 10:
        return f"Ci vuole impegno! Ti serve {grade_text} da 10 (arrotondato da {display_grade}) per raggiungere l'obiettivo."
    elif raw_grade >= 9:
        return f"Devi impegnarti molto: ti serve {grade_text} da almeno {display_grade} per raggiungere l'obiettivo."
    elif raw_grade >= 7:
        return f"È fattibile: Con {grade_text} da {display_grade} puoi raggiungere {target_average}."
    elif raw_grade >= 6:
        return f"Ci sei quasi! {grade_text.capitalize()} da {display_grade} ti permetterà di raggiungere l'obiettivo."
    else:
        return f"Ottimo! Anche con {grade_text} modesti ({display_grade}) raggiungerai {target_average}."

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
        
        # Extract current grades
        current_grades = []
        for g in subject_data['grades']:
            if isinstance(g, dict) and 'decimalValue' in g and g['decimalValue'] is not None:
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
    grade_text = "un voto" if num_grades == 1 else f"{num_grades} voti"
    
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

def get_all_grades(grades_avr):
    """
    Collect all grades from all subjects in all periods (excluding blue grades)
    
    Args:
        grades_avr: Dictionary containing grades organized by period and subject
    
    Returns:
        List of decimal grade values (blue grades excluded)
    """
    all_grades_list = []
    for period in grades_avr:
        if period == 'all_avr':
            continue
        for subject in grades_avr[period]:
            if subject == 'period_avr':
                continue
            for grade in grades_avr[period][subject].get('grades', []):
                # Always exclude blue grades as requested
                if not grade.get('isBlue', False):
                    all_grades_list.append(grade['decimalValue'])
    return all_grades_list

@app.route('/calculate_goal_overall', methods=['POST'])
def calculate_goal_overall():
    """Calculate what grades are needed to reach a target overall average.
    If subject is provided, calculates for that subject. Otherwise, suggests best subjects to focus on."""
    if 'grades_avr' not in flask.session:
        return flask.jsonify({'error': 'No active session'}), 401
    
    try:
        data = flask.request.get_json()
        subject = data.get('subject')  # Optional
        target_overall_average = float(data.get('target_average'))
        num_grades_input = data.get('num_grades')  # Optional - will auto-calculate if not provided
        
        grades_avr = flask.session['grades_avr']
        
        # Validate inputs
        if target_overall_average < 1 or target_overall_average > 10:
            return flask.jsonify({'error': 'La media target deve essere tra 1 e 10'}), 400
        
        # Get current overall average
        current_overall_average = grades_avr.get('all_avr', 0)
        
        # Validate that target is achievable
        if target_overall_average < current_overall_average:
            return flask.jsonify({'error': f'La media target ({target_overall_average}) non può essere inferiore alla media generale attuale ({round(current_overall_average, 2)}).'}), 400
        
        # Collect all current grades from all subjects in all periods (excluding blue grades)
        all_grades_list = get_all_grades(grades_avr)
        
        if not all_grades_list:
            return flask.jsonify({'error': 'Nessun voto disponibile'}), 400
        
        current_total = sum(all_grades_list)
        current_count = len(all_grades_list)
        
        # Auto-calculate num_grades if not provided, otherwise use provided value
        if num_grades_input is None:
            num_grades, _ = calculate_optimal_grades_needed(current_total, current_count, target_overall_average)
            auto_calculated = True
        else:
            num_grades = int(num_grades_input)
            auto_calculated = False
            if num_grades < 1 or num_grades > 10:
                return flask.jsonify({'error': 'Il numero di voti deve essere tra 1 e 10'}), 400
        
        # Calculate required sum for new grades
        required_sum = target_overall_average * (current_count + num_grades) - current_total
        required_average_grade = required_sum / num_grades
        
        # If no subject specified, suggest the best subjects to focus on
        if not subject:
            suggestions = calculate_subject_suggestions(grades_avr, target_overall_average, num_grades, required_average_grade)
            
            return flask.jsonify({
                'success': True,
                'current_overall_average': round(current_overall_average, 2),
                'target_average': target_overall_average,
                'suggestions': suggestions,
                'num_grades': num_grades,
                'auto_calculated': auto_calculated,
                'message': get_smart_suggestion_message(suggestions, target_overall_average, num_grades)
            }), 200
        
        # If subject is specified, calculate for that specific subject
        # Find the subject in any period
        subject_found = False
        for period in grades_avr:
            if period == 'all_avr':
                continue
            if subject in grades_avr[period] and grades_avr[period][subject] != 'period_avr':
                subject_found = True
                break
        
        if not subject_found:
            return flask.jsonify({'error': 'Materia non trovata'}), 400
        
        # Round to nearest allowed grade
        display_grade = round_to_allowed_grade(required_average_grade)
        
        required_grades = [display_grade] * num_grades
        achievable = min(ALLOWED_GRADES) <= required_average_grade <= max(ALLOWED_GRADES)
        
        return flask.jsonify({
            'success': True,
            'current_overall_average': round(current_overall_average, 2),
            'target_average': target_overall_average,
            'required_grade': display_grade,
            'required_grades': required_grades,
            'current_grades_count': current_count,
            'achievable': achievable,
            'subject': subject,
            'message': get_goal_overall_message(required_average_grade, display_grade, target_overall_average, current_overall_average, num_grades, subject)
        }), 200
        
    except ValueError as e:
        return flask.jsonify({'error': 'Valori non validi'}), 400
    except Exception as e:
        logger.error(f"Error calculating overall goal: {e}", exc_info=True)
        return flask.jsonify({'error': 'Errore durante il calcolo'}), 500

def calculate_optimal_grades_needed(current_total, current_count, target_average):
    """Calculate the optimal/minimum number of grades needed to reach target average.
    
    Uses a heuristic: assume we can get perfect 10s, calculate minimum grades needed.
    Then provide a realistic plan with achievable grades.
    """
    # If already at or above target, no grades needed
    if current_count > 0 and (current_total / current_count) >= target_average:
        return 0, []
    
    # Calculate minimum grades needed assuming perfect 10s
    # Formula: (current_total + 10*n) / (current_count + n) = target_average
    # Solving for n: n = (current_total - target_average * current_count) / (target_average - 10)
    
    min_grades_needed = 1
    if target_average < 10:
        numerator = target_average * current_count - current_total
        denominator = 10 - target_average
        if denominator > 0:
            min_grades_needed = max(1, int(numerator / denominator) + 1)
    
    # Cap at reasonable number
    min_grades_needed = min(min_grades_needed, 5)
    
    # Calculate what grades are actually needed (realistic, not just 10s)
    required_sum = target_average * (current_count + min_grades_needed) - current_total
    required_average_grade = required_sum / min_grades_needed
    
    # If required grade is too high (>10), we need more grades at lower values
    while required_average_grade > 10 and min_grades_needed < 10:
        min_grades_needed += 1
        required_sum = target_average * (current_count + min_grades_needed) - current_total
        required_average_grade = required_sum / min_grades_needed
    
    grades_plan = [round(required_average_grade, 1)] * min_grades_needed
    
    return min_grades_needed, grades_plan

def calculate_subject_suggestions(grades_avr, target_overall_average, num_grades, baseline_required_grade):
    """Calculate which subjects would be easiest to focus on to reach the target overall average.
    Returns suggestions sorted by difficulty (easiest first).
    
    The algorithm uses a combined scoring approach:
    - Difficulty: Lower current averages = easier targets (more room for improvement)
    - Impact: Fewer existing grades = higher impact per new grade
    - Combined score balances both factors to find optimal subjects
    """
    suggestions = []
    
    # Get all unique subjects across all periods
    all_subjects = set()
    for period in grades_avr:
        if period == 'all_avr':
            continue
        for subject in grades_avr[period]:
            if subject != 'period_avr':
                all_subjects.add(subject)
    
    # For each subject, calculate what grade is needed and score difficulty
    for subject in all_subjects:
        # Get current average for this subject (across all periods)
        subject_grades = []
        for period in grades_avr:
            if period == 'all_avr':
                continue
            if subject in grades_avr[period]:
                subject_data = grades_avr[period][subject]
                if 'grades' in subject_data:
                    subject_grades.extend([g['decimalValue'] for g in subject_data['grades'] if not g.get('isBlue', False)])
        
        if not subject_grades:
            continue
        
        current_subject_avg = sum(subject_grades) / len(subject_grades)
        
        # Difficulty calculation: measures how much "easier" a subject is to improve
        # Formula: baseline_grade - (target - current_avg)
        # - If current_avg is low, (target - current_avg) is high, making the result lower (easier)
        # - Lower scores = easier targets
        difficulty_score = baseline_required_grade - (target_overall_average - current_subject_avg)
        
        # Impact factor: subjects with fewer grades have more impact per new grade
        impact_factor = 1.0 / (len(subject_grades) + num_grades) * 100
        
        # Combined score: prioritize subjects that are both easier AND have higher impact
        combined_score = difficulty_score - (impact_factor * SUGGESTION_IMPACT_WEIGHT)
        
        suggestions.append({
            'subject': subject,
            'current_average': round(current_subject_avg, 2),
            'required_grade': round_to_allowed_grade(min(baseline_required_grade, 10)),
            'num_current_grades': len(subject_grades),
            'difficulty': round(combined_score, 2),
            'impact': round(impact_factor, 2)
        })
    
    # Sort by combined difficulty score (ascending) - lower = better target
    suggestions.sort(key=lambda x: x['difficulty'])
    
    # Return top suggestions
    return suggestions[:MAX_SUGGESTIONS]

def calculate_period_subject_suggestions(grades_avr, period, target_average, num_grades):
    """Calculate which subjects within a period would be easiest to focus on to reach the target average.
    Returns suggestions sorted by difficulty (easiest first).
    
    The algorithm uses a combined scoring approach:
    - Difficulty: Lower current averages = easier targets (more room for improvement)
    - Impact: Fewer existing grades = higher impact per new grade
    - Combined score balances both factors to find optimal subjects
    """
    suggestions = []
    
    # Get all subjects in the period
    if period not in grades_avr or period == 'all_avr':
        return []
    
    period_subjects = [s for s in grades_avr[period].keys() if s != 'period_avr']
    
    # Calculate baseline required grade (what would be needed on average)
    # This is used as a reference point for difficulty calculation
    all_period_grades = []
    for subject in period_subjects:
        subject_data = grades_avr[period][subject]
        if 'grades' in subject_data:
            for g in subject_data['grades']:
                if not g.get('isBlue', False):
                    all_period_grades.append(g['decimalValue'])
    
    if not all_period_grades:
        return []
    
    current_period_total = sum(all_period_grades)
    current_period_count = len(all_period_grades)
    
    # Calculate baseline grade needed (assuming distributed evenly across all subjects)
    required_sum = target_average * (current_period_count + num_grades) - current_period_total
    baseline_required_grade = required_sum / num_grades
    
    # For each subject in the period, calculate what grade is needed and score difficulty
    for subject in period_subjects:
        subject_data = grades_avr[period][subject]
        
        # Get grades for this subject
        subject_grades = []
        if 'grades' in subject_data:
            subject_grades = [g['decimalValue'] for g in subject_data['grades'] if not g.get('isBlue', False)]
        
        if not subject_grades:
            continue
        
        current_subject_avg = sum(subject_grades) / len(subject_grades)
        num_subject_grades = len(subject_grades)
        sum_subject_grades = sum(subject_grades)
        
        # Calculate what grade is needed in this subject to reach the period target
        # Formula derivation:
        # Let X = required grade in this subject
        # Target equation: (period_total_without_subject + X*num_grades) / (period_count_without_subject + num_grades) = target_average
        # Solving for X:
        # X = (target_average * (period_count_without_subject + num_grades) - period_total_without_subject) / num_grades
        
        # Remove this subject's current grades from the period total
        period_total_without_subject = current_period_total - sum_subject_grades
        period_count_without_subject = current_period_count - num_subject_grades
        
        # Calculate required grade in this subject
        required_grade_subject = (target_average * (period_count_without_subject + num_grades) - period_total_without_subject) / num_grades
        
        # Difficulty calculation: Lower scores = easier targets
        # The formula considers two factors:
        # 1. Gap to target (target - current_avg): Larger gaps make it harder
        # 2. Baseline difficulty (baseline_required_grade): Overall difficulty level
        # Combined: baseline_grade - gap_to_target
        # Result: Subjects with low current averages get lower (easier) scores
        difficulty_score = baseline_required_grade - (target_average - current_subject_avg)
        
        # Impact factor: subjects with fewer grades have more impact per new grade
        impact_factor = 1.0 / (num_subject_grades + num_grades) * 100
        
        # Combined score: prioritize subjects that are both easier AND have higher impact
        combined_score = difficulty_score - (impact_factor * SUGGESTION_IMPACT_WEIGHT)
        
        suggestions.append({
            'subject': subject,
            'current_average': round(current_subject_avg, 2),
            'required_grade': round_to_allowed_grade(min(required_grade_subject, 10)),
            'num_current_grades': num_subject_grades,
            'difficulty': round(combined_score, 2),
            'impact': round(impact_factor, 2)
        })
    
    # Sort by combined difficulty score (ascending) - lower = better target
    suggestions.sort(key=lambda x: x['difficulty'])
    
    # Return top suggestions
    return suggestions[:MAX_SUGGESTIONS]

def get_period_suggestion_message(suggestions, target_average, num_grades, period):
    """Generate an intelligent message about which subjects to focus on within a period"""
    if not suggestions:
        return f"Nessuna materia disponibile per il periodo {period}."
    
    grade_text = "un voto" if num_grades == 1 else f"{num_grades} voti"
    
    if suggestions[0]['required_grade'] > 10:
        return f"⚠️ Raggiungere {target_average} nel periodo {period} è molto difficile. Serve impegno in tutte le materie!"
    elif suggestions[0]['required_grade'] >= 9:
        top_subject = suggestions[0]['subject']
        return f"💪 Concentrati su {top_subject}! Servono {grade_text} da {suggestions[0]['required_grade']} per raggiungere {target_average} nel periodo {period}."
    elif suggestions[0]['required_grade'] >= 7:
        return f"✅ Obiettivo raggiungibile! Le materie consigliate sono elencate sotto - concentrati su quelle con voti più bassi!"
    else:
        return f"🎉 Ottimo! Anche con {grade_text} modesti puoi raggiungere {target_average} nel periodo {period}!"

def get_smart_suggestion_message(suggestions, target_average, num_grades):
    """Generate an intelligent message about which subjects to focus on"""
    if not suggestions:
        return "Nessuna materia disponibile per il calcolo."
    
    grade_text = "un voto" if num_grades == 1 else f"{num_grades} voti"
    
    if suggestions[0]['required_grade'] > 10:
        return f"⚠️ Raggiungere {target_average} di media generale è molto difficile. Serve impegno in tutte le materie!"
    elif suggestions[0]['required_grade'] >= 9:
        top_subject = suggestions[0]['subject']
        return f"💪 Concentrati su {top_subject}! Servono {grade_text} da {suggestions[0]['required_grade']} per raggiungere la media generale di {target_average}."
    elif suggestions[0]['required_grade'] >= 7:
        return f"✅ Obiettivo raggiungibile! Le materie consigliate sono elencate sotto - concentrati su quelle con voti più bassi!"
    else:
        return f"🎉 Ottimo! Anche con {grade_text} modesti puoi raggiungere {target_average} di media generale!"

def get_goal_overall_message(raw_grade, display_grade, target_average, current_average, num_grades, subject):
    """Generate message for overall average goal calculation"""
    grade_text = "un voto" if num_grades == 1 else f"{num_grades} voti"
    
    if raw_grade < min(ALLOWED_GRADES):
        return f"Ottimo! La tua media generale è già sopra l'obiettivo. Anche con voti minimi in {subject} raggiungerai {target_average}."
    elif raw_grade > max(ALLOWED_GRADES):
        return f"Purtroppo non è possibile raggiungere {target_average} di media generale con {grade_text} in {subject}. Prova un obiettivo più realistico!"
    elif display_grade >= 9.5:
        return f"Ci vuole impegno! Ti serve {grade_text} da {display_grade} in {subject} per raggiungere la media generale di {target_average}."
    elif raw_grade >= 9:
        return f"Devi impegnarti molto: ti serve {grade_text} da almeno {display_grade} in {subject} per raggiungere la media generale di {target_average}."
    elif raw_grade >= 7:
        return f"È fattibile: Con {grade_text} da {display_grade} in {subject} puoi raggiungere la media generale di {target_average}."
    elif raw_grade >= 6:
        return f"Ci sei quasi! {grade_text.capitalize()} da {display_grade} in {subject} ti permetterà di raggiungere la media generale di {target_average}."
    else:
        return f"Ottimo! Anche con {grade_text} modesti ({display_grade}) in {subject} raggiungerai la media generale di {target_average}."

@app.route('/predict_average_overall', methods=['POST'])
def predict_average_overall():
    """Predict how hypothetical grades in a subject will affect the overall average"""
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
        
        # Get current overall average
        current_overall_average = grades_avr.get('all_avr', 0)
        
        # Collect all current grades from all subjects in all periods (excluding blue grades)
        all_grades_list = get_all_grades(grades_avr)
        
        if not all_grades_list:
            return flask.jsonify({'error': 'Nessun voto disponibile'}), 400
        
        # Calculate predicted overall average with new grades added
        all_grades_with_predicted = all_grades_list + predicted_grades
        predicted_overall_average = sum(all_grades_with_predicted) / len(all_grades_with_predicted)
        
        # Calculate change
        change = predicted_overall_average - current_overall_average
        
        # Generate message
        message = get_predict_overall_message(change, predicted_overall_average, len(predicted_grades), subject)
        
        return flask.jsonify({
            'success': True,
            'current_overall_average': round(current_overall_average, 2),
            'predicted_overall_average': round(predicted_overall_average, 2),
            'change': round(change, 2),
            'num_predicted_grades': len(predicted_grades),
            'subject': subject,
            'period': period,
            'message': message
        }), 200
        
    except ValueError as e:
        return flask.jsonify({'error': 'Valori non validi'}), 400
    except Exception as e:
        logger.error(f"Error predicting overall average: {e}", exc_info=True)
        return flask.jsonify({'error': 'Errore durante il calcolo'}), 500

def get_predict_overall_message(change, predicted_average, num_grades, subject):
    """Generate a helpful message for overall average prediction"""
    grade_text = "un voto" if num_grades == 1 else f"{num_grades} voti"
    
    if change > 0.5:
        return f"Ottimo! Con {grade_text} in {subject} la tua media generale salirebbe a {round(predicted_average, 2)} ({change:+.2f})! 📈"
    elif change > 0:
        return f"Bene! Con {grade_text} in {subject} la tua media generale migliorerebbe leggermente a {round(predicted_average, 2)} ({change:+.2f}). ✅"
    elif change == 0:
        return f"Con {grade_text} in {subject} la tua media generale rimarrebbe stabile a {round(predicted_average, 2)}. ➡️"
    elif change > -0.5:
        return f"Attenzione! Con {grade_text} in {subject} la tua media generale scenderebbe leggermente a {round(predicted_average, 2)} ({change:.2f}). ⚠️"
    else:
        return f"Attenzione! Con {grade_text} in {subject} la tua media generale scenderebbe significativamente a {round(predicted_average, 2)} ({change:.2f}). 📉"

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
    app.run(host='0.0.0.0', port=8001)
    # app.run(debug=True)

