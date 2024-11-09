from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import pandas as pd
import base64
import json
import requests
import os
import glob

app = Flask(__name__)
cf_port = os.getenv("PORT", 3000)

default_api_url = "https://jsonplaceholder.typicode.com/todos/1"
gcp = '.app.commissions.cloud.sap'
legacy = '.callidusondemand.com'

plan = '/api/v2/'
gcp_plan = '/mtsvc/tcmp/rest/v2/plans?$filter=name eq'
total = '?skip=0&top=100'
api_data = []

def files_remove():
    delete_path = '.'  # Replace with the desired directory path
    file_extensions = ['*.xlsx']
    files_to_delete = [file for ext in file_extensions for file in glob.glob(os.path.join(delete_path, ext))]
    for file_to_delete in files_to_delete:
        try:
            os.remove(file_to_delete)
            print(f"The file '{file_to_delete}' has been deleted.")
        except Exception as e:
            print(f"An error occurred while deleting the file '{file_to_delete}': {str(e)}")

def import_from_excel():
    try:
        df = pd.read_excel("imported_data.xlsx")
        return df.to_dict(orient='records')
    except FileNotFoundError:
        return []

@app.route("/")
def home():
    return redirect(url_for('import_data'))

@app.route("/index", methods=["GET", "POST"])
def index():
    data = None
    jsoncount = 0
    api_url = default_api_url
    global api_data
    global input1, input5
    api_data = []
    if request.method == "POST":
        input1 = request.form.get("tenant")
        input2 = request.form.get("username")
        input3 = request.form.get("password")
        input4 = request.form.get("platform")
        input5 = request.form.get("dataTypes")

        usrPass = f"{input2}:{input3}"
        b64Val = base64.b64encode(usrPass.encode()).decode()

        if input4 == "GCP":
            api_url = f'https://{input1}{gcp}{gcp_plan}{input5}{total}'
        elif input4 in ["HANA", "Oracle"]:
            api_url = f'https://{input1}{legacy}{plan}{input5}{total}'

        try:
            files_remove()
            headers = {'authorization': f"Basic {b64Val}", 'cache-control': "no-cache", 'Content-Type': "application/json"}
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(e)
            return render_template('error.html', error_message=e)

        if response.status_code == 200:
            data = response.json()
            json_str = json.loads(json.dumps(data[input5]))
            jsoncount = len(json_str)

            data_mapping = {
                "creditTypes": lambda entry: {'creditTypeId': entry['creditTypeId'], 'description': entry['description']},
                "eventTypes": lambda entry: {'eventTypeId': entry['eventTypeId'], 'description': entry['description']},
                "earningCodes": lambda entry: {'earningCodeId': entry['earningCodeId'], 'description': entry['description']},
                "earningGroups": lambda entry: {'earningGroupId': entry['earningGroupId'], 'description': entry['description']},
                "positionGroups": lambda entry: {'name': entry['name'], 'description': ''},
                "reasons": lambda entry: {'reasonId': entry['reasonId'], 'description': entry['description']}
            }

            if input5 in data_mapping:
                api_data = [data_mapping[input5](entry) for entry in json_str]
            else:
                print("No Data")

    return render_template('index.html', api_data=api_data, count=jsoncount)

@app.route('/export', methods=["POST"])
def export_to_excel():
    global input1, input5
    df = pd.DataFrame(api_data)
    excel_path = f'{input1}_{input5}.xlsx'
    df.to_excel(excel_path, index=False)
    return send_file(excel_path, as_attachment=True)

@app.route('/export1', methods=["GET", "POST"])
def export_data():
    export_to_excel()
    return jsonify({"message": "Data exported successfully"})

@app.route('/import', methods=["GET", "POST"])
def import_data():
    data = None
    error_details = []
    success_count = 0
    error_count = 0
    api_url = default_api_url
    if request.method == "POST":
        global input1, input2, input3, input4, input5
        input1 = request.form.get("tenant")
        input2 = request.form.get("username")
        input3 = request.form.get("password")
        input4 = request.form.get("platform")
        input5 = request.form.get("dataTypes")

        uploaded_file = request.files['file']
        df = pd.read_excel(uploaded_file).fillna(" ")
        data_list = json.dumps(df.to_dict(orient='records'), indent=4)

        usrPass = f"{input2}:{input3}"
        b64Val = base64.b64encode(usrPass.encode()).decode()

        if input4 == "GCP":
            api_url = f'https://{input1}{gcp}{gcp_plan}{input5}{total}'
        elif input4 in ["HANA", "Oracle"]:
            api_url = f'https://{input1}{legacy}{plan}{input5}'

        try:
            files_remove()
            headers = {'authorization': f"Basic {b64Val}", 'Content-Type': "application/json"}
            #print(api_url)
            #print(data_list)
            response = requests.post(api_url, headers=headers, data=data_list)
            #print(response.text)
            if response.status_code in [201, 207, 400]:
                data = response.json()
                json_str = json.loads(json.dumps(data[input5]))
                error_data = json_str

                if response.status_code == 201:
                    success_count = sum('dataTypeSeq' in record for record in data[input5])
                elif response.status_code == 207:
                    error_messages = [{'Row': index + 1, 'Error Message': error['_ERROR_']} for index, error in enumerate(error_data) if '_ERROR_' in error]
                    success_count = sum('dataTypeSeq' in record for record in data[input5])
                elif response.status_code == 400:
                    error_messages = [{'Row': index + 1, 'Error Message': error['_ERROR_']} for index, error in enumerate(error_data) if '_ERROR_' in error]
                error_details = error_messages
                error_count = len(error_details)
            elif response.status_code == 500:
                success_count += 1
            else:
                error_details = ["Error parsing response"]
        except requests.exceptions.RequestException as e:
            print(e)
            error_details.append({'Row': 0, 'Error Message': str(e)})

    return render_template('import.html', data=error_details, success_count=success_count, error_count=error_count)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(cf_port), debug=True)