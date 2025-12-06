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
APP_VERSION = "1.7.6"

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
        
        # Round grades >= GRADE_ROUNDING_THRESHOLD to 10 for display purposes
        display_grade = required_average_grade
        if GRADE_ROUNDING_THRESHOLD <= required_average_grade <= 10:
            display_grade = 10
        
        # Note: For simplicity and clarity, we assume all required grades are the same
        # This gives the student a single, clear target to aim for across all tests
        required_grades = [display_grade] * num_grades
        
        # Determine if it's achievable (use original value for comparison, but allow GRADE_ROUNDING_THRESHOLD+ to round to 10)
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
    elif GRADE_ROUNDING_THRESHOLD <= raw_grade <= 10:
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
        subject = data.get('subject')  # Optional now
        target_overall_average = float(data.get('target_average'))
        num_grades = int(data.get('num_grades', 1))
        
        grades_avr = flask.session['grades_avr']
        
        # Validate inputs
        if target_overall_average < 1 or target_overall_average > 10:
            return flask.jsonify({'error': 'La media target deve essere tra 1 e 10'}), 400
        
        if num_grades < 1 or num_grades > 10:
            return flask.jsonify({'error': 'Il numero di voti deve essere tra 1 e 10'}), 400
        
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
        
        # Round grades >= GRADE_ROUNDING_THRESHOLD to 10 for display
        display_grade = required_average_grade
        if GRADE_ROUNDING_THRESHOLD <= required_average_grade <= 10:
            display_grade = 10
        
        required_grades = [display_grade] * num_grades
        achievable = 1 <= required_average_grade <= 10
        
        return flask.jsonify({
            'success': True,
            'current_overall_average': round(current_overall_average, 2),
            'target_average': target_overall_average,
            'required_grade': round(display_grade, 2),
            'required_grades': [round(g, 2) for g in required_grades],
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
            'required_grade': round(min(baseline_required_grade, 10), 2),
            'num_current_grades': len(subject_grades),
            'difficulty': round(combined_score, 2),
            'impact': round(impact_factor, 2)
        })
    
    # Sort by combined difficulty score (ascending) - lower = better target
    suggestions.sort(key=lambda x: x['difficulty'])
    
    # Return top suggestions
    return suggestions[:MAX_SUGGESTIONS]

def get_smart_suggestion_message(suggestions, target_average, num_grades):
    """Generate an intelligent message about which subjects to focus on"""
    if not suggestions:
        return "Nessuna materia disponibile per il calcolo."
    
    grade_text = "voto" if num_grades == 1 else f"{num_grades} voti"
    
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
    grade_text = "voto" if num_grades == 1 else f"{num_grades} voti"
    
    if raw_grade < 1:
        return f"Ottimo! La tua media generale è già sopra l'obiettivo. Anche con voti minimi in {subject} raggiungerai {target_average}."
    elif raw_grade > 10:
        return f"Purtroppo non è possibile raggiungere {target_average} di media generale con {grade_text} in {subject}. Prova un obiettivo più realistico!"
    elif GRADE_ROUNDING_THRESHOLD <= raw_grade <= 10:
        return f"Ci vuole impegno! Ti servono {grade_text} da 10 in {subject} (arrotondato da {round(raw_grade, 2)}) per raggiungere la media generale di {target_average}."
    elif raw_grade >= 9:
        return f"Devi impegnarti molto: ti servono {grade_text} da almeno {round(raw_grade, 1)} in {subject} per raggiungere la media generale di {target_average}."
    elif raw_grade >= 7:
        return f"È fattibile: Con {grade_text} da {round(raw_grade, 1)} in {subject} puoi raggiungere la media generale di {target_average}."
    elif raw_grade >= 6:
        return f"Ci sei quasi! {grade_text.capitalize()} da {round(raw_grade, 1)} in {subject} ti permetteranno di raggiungere la media generale di {target_average}."
    else:
        return f"Ottimo! Anche con {grade_text} modesti ({round(raw_grade, 1)}) in {subject} raggiungerai la media generale di {target_average}."

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
    grade_text = "voto" if num_grades == 1 else f"{num_grades} voti"
    
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

