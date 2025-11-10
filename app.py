import requests
import json
import flask
import os
import secrets
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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
        
        # Store token and student_id in session for later use
        flask.session['token'] = token
        student_id = "".join(filter(str.isdigit, user_id))
        flask.session['student_id'] = student_id
        
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

@app.route('/export-pdf')
def export_pdf():
    """Export grades as a PDF report"""
    # Check if user has a valid session
    if 'token' not in flask.session or 'student_id' not in flask.session:
        return flask.redirect('/')
    
    token = flask.session.get('token')
    student_id = flask.session.get('student_id')
    
    try:
        # Get grades data
        grades_data = get_grades(student_id, token)
        grades_avr = calculate_avr(grades_data)
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, 
                              topMargin=2*cm, bottomMargin=2*cm)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#f03333'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#c83737'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        # Add title
        title = Paragraph("📊 Riepilogo Voti - che media ho?", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.5*cm))
        
        # Add generation date
        date_text = f"Generato il: {datetime.now().strftime('%d/%m/%Y alle %H:%M')}"
        date_para = Paragraph(date_text, styles['Normal'])
        elements.append(date_para)
        elements.append(Spacer(1, 0.5*cm))
        
        # Add overall average
        overall_avg = grades_avr.get('all_avr', 0)
        avg_color = colors.HexColor('#4caf50') if overall_avg >= 8 else \
                   colors.HexColor('#4facfe') if overall_avg >= 7 else \
                   colors.HexColor('#ffa500') if overall_avg >= 6 else \
                   colors.HexColor('#f03333')
        
        avg_style = ParagraphStyle(
            'AvgStyle',
            parent=styles['Normal'],
            fontSize=18,
            textColor=avg_color,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        avg_text = f"Media Generale: {overall_avg:.1f}"
        avg_para = Paragraph(avg_text, avg_style)
        elements.append(avg_para)
        elements.append(Spacer(1, 1*cm))
        
        # Add grades by period
        for period, subjects in grades_avr.items():
            if period == 'all_avr':
                continue
                
            # Period header
            period_avg = subjects.get('period_avr', 0)
            period_title = f"Periodo {period} - Media: {period_avg:.1f}"
            period_para = Paragraph(period_title, heading_style)
            elements.append(period_para)
            elements.append(Spacer(1, 0.3*cm))
            
            # Create table for subjects
            table_data = [['Materia', 'Media', 'Voti']]
            
            for subject, data in subjects.items():
                if subject == 'period_avr':
                    continue
                    
                subject_avg = data.get('avr', 0)
                grades_list = [str(g['decimalValue']) for g in data.get('grades', [])]
                grades_str = ', '.join(grades_list)
                
                table_data.append([subject, f"{subject_avg:.1f}", grades_str])
            
            # Create and style table
            if len(table_data) > 1:
                table = Table(table_data, colWidths=[6*cm, 2*cm, 8*cm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c83737')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
                ]))
                elements.append(table)
                elements.append(Spacer(1, 0.8*cm))
        
        # Add footer
        elements.append(Spacer(1, 1*cm))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        footer = Paragraph("Generato da chemediaho - https://github.com/gablilli/chemediaho", footer_style)
        elements.append(footer)
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF from buffer
        pdf = buffer.getvalue()
        buffer.close()
        
        # Create response
        response = flask.make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=voti_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        return response
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return flask.render_template('login.html', error="Errore durante l'esportazione del PDF. Riprova.")

    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
    # app.run(debug=True)

