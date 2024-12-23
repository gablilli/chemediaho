import requests
import json
import flask

app = flask.Flask(__name__)
@app.route('/')
def home():
    return flask.render_template('login.html')

@app.route('/login', methods=['POST'])
def login_route():
    user_id = flask.request.form['user_id']
    user_pass = flask.request.form['user_pass']
    try:
        login_response = login(user_id, user_pass)
        token = login_response["token"]
        if token is None or token == "":
            return "Invalid token", 401
        student_id = "".join(filter(str.isdigit, user_id))
        grades_avr = calculate_avr(get_grades(student_id, token))
        return flask.render_template('grades.html', grades_avr=grades_avr)
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}", 500
    except Exception as e:
        return f"An error occurred: {e}", 500
        

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
        return response.json()
    else:
        response.raise_for_status()

def calculate_avr(grades):
    grades_avr = {}
    for grade in grades["grades"]:
        if grade["noAverage"] is True:
            continue
        if grades_avr.get(grade["subjectDesc"]) is None:
            grades_avr[grade["subjectDesc"]] = {"count": 0, "avr": 0, "grades": []}
        grades_avr[grade["subjectDesc"]]["count"] += 1
        if grade["decimalValue"] is None:
            grade["decimalValue"] = 0
        grades_avr[grade["subjectDesc"]]["grades"].append(grade["decimalValue"])
    for subject in grades_avr:
        grades_avr[subject]["avr"] = sum(grades_avr[subject]["grades"]) / grades_avr[subject]["count"]
    return grades_avr   
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
