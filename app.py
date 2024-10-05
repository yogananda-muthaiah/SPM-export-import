from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import pandas as pd
import base64
import json
import requests
import os
import openpyxl
import glob


app = Flask(__name__)
cf_port = os.getenv("PORT", 3000)

default_api_url = "https://jsonplaceholder.typicode.com/todos/1"
gcp = '.app.commissions.cloud.sap'
legacy = '.callidusondemand.com'

plan = '/api/v2/'
quote = "'"
gcp_plan = '/mtsvc/tcmp/rest/v2/plans?$filter=name eq'
platform = 'HANA'
total = '?skip=0&top=100'
api_data = []


def files_remove():
    # Define the path where you want to delete files
    delete_path = '.'  # Replace with the desired directory path
    # Define the file extensions you want to delete
    file_extensions = ['*.xlsx']

    for ext in file_extensions:
        # Construct the full path with the file extension pattern
        files_to_delete = glob.glob(os.path.join(delete_path, ext))
        
        for file_to_delete in files_to_delete:
            try:
                # Attempt to delete the file
                os.remove(file_to_delete)
                print(f"The file '{file_to_delete}' has been deleted.")
            except Exception as e:
                print(f"An error occurred while deleting the file '{file_to_delete}': {str(e)}")




# Function to import data from Excel
def import_from_excel():
    try:
        df = pd.read_excel("imported_data.xlsx")
        return df.to_dict(orient='records')
    except FileNotFoundError:
        return []

@app.route("/index", methods=["GET", "POST"])
def index():
    data = None
    jsoncount = 0
    #print(request.form)
    api_url = default_api_url
    global api_data
    api_data = []
    if request.method == "POST":
        global input1
        input1 = request.form.get("tenant")
        print(input1)
        input2 = request.form.get("username")
        print(input2)
        input3 = request.form.get("password")
        print(input3)
        input4 = request.form.get("platform")
        #input4 = 'HANA'
        print(input4)
        global input5
        input5 = request.form.get("dataTypes")
        #input5 = 'creditTypes'
        print(input5)
    
        usrPass = str(input2) + ':' + input3
        b64Val = base64.b64encode(usrPass.encode()).decode()    
        
        print(b64Val)
        print("login ----- " + input2 + "-----password ----" + input1 + "------tenant ----" + input3 + "------platform ----" + input4 + "--------plan ----" + input5)

        # Determine the selected option in Input 3
        if input4 == "GCP":
            api_url = str('https://'+ input1 + gcp + gcp_plan + input5 + total)
        elif input4 == "HANA":
            api_url = str('https://' + input1 + legacy + plan + input5 + total)
        elif input4 == "Oracle":
            api_url = str('https://' + input1 + legacy + plan + input5 + total)

        try:
            # Make an API request to fetch data
            files_remove()
            print(api_url)
            headers = {'authorization': "Basic %s" % b64Val, 'cache-control': "no-cache",     'Content-Type': "application/json"}
            response = requests.get(api_url, headers=headers)
            #print(response.json)
            response.raise_for_status()

        except requests.exceptions.RequestException as e:
            # Handle exceptions, for example, print an error message
            print(e)
            return render_template('error.html', error_message=e)
            print("API request failed:", e)            
        
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            json_str = json.dumps(data[input5])
            json_str = json.loads(json_str)
            #print(json_str)
            jsoncount = len(json_str)
            #print(a)
            # Extract 'creditTypeId' values
            if input5 == "creditTypes" and len(json_str)>0:
                data1 = [{'creditTypeId': entry['creditTypeId'], 'description': entry['description']} for entry in json_str]
                
                api_data = data1
                #print(api_data)
            elif input5 == "eventTypes":    
                api_data = [{'eventTypeId': entry['eventTypeId'], 'description': entry['description']} for entry in json_str]
                #print(api_data)
            elif input5 == "earningCodes":    
                api_data = [{'earningCodeId': entry['earningCodeId'], 'description': entry['description']} for entry in json_str]    
            elif input5 == "earningGroups":    
                api_data= [{'earningGroupId': entry['earningGroupId'], 'description': entry['description']} for entry in json_str]
            elif input5 == "positionGroups":    
                api_data = [{'name': entry['name'], 'description': ''} for entry in json_str]
            elif input5 == "reasons":
                api_data = [{'reasonId': entry['reasonId'], 'description': entry['description']} for entry in json_str]
            else:    
                print("No Data")

            
            #print(api_data)
        
    return render_template('index.html', api_data=api_data, count=jsoncount)


@app.route('/export', methods=["POST"])
def export_to_excel():
    df = pd.DataFrame(api_data)
    excel_path = f'{input1}_{input5}.xlsx'
    df.to_excel(excel_path, index=False)# Replace with your desired path
    return send_file(excel_path, as_attachment=True)



@app.route('/export1', methods=["GET", "POST"])
def export_data():
    selected_ids = request.form.getlist('selected_ids[]')
    selected_data = [item for item in api_data if str(item['id']) in selected_ids]
    export_to_excel(selected_data)
    return jsonify({"message": "Data exported successfully"})



@app.route('/import', methods=["GET", "POST"])
def import_data():
    data = None
    error_details = []
    success_count = 0
    error_count = 0
    #print(request.form)
    api_url = default_api_url
    if request.method == "POST":
        global input1
        input1 = request.form.get("tenant")
        print(input1)
        input2 = request.form.get("username")
        print(input2)
        input3 = request.form.get("password")
        print(input3)
        input4 = request.form.get("platform")
        #input4 = 'HANA'
        print(input4)
        global input5
        input5 = request.form.get("dataTypes")
        #input5 = 'creditTypes'
        print(input5)
        
        
        uploaded_file = request.files['file']
        #print(uploaded_file)
        # Read the Excel file into a pandas DataFrame
        df = pd.read_excel(uploaded_file)
        
        df = df.fillna(" ")
        # Convert the DataFrame to a list of dictionaries
        data_list = df.to_dict(orient='records')
        data_list = json.dumps(data_list, indent=4)
        print(data_list)
        
        usrPass = str(input2) + ':' + input3
        b64Val = base64.b64encode(usrPass.encode()).decode()    
        
        print(b64Val)
        print("login ----- " + input2 + "-----password ----" + input1 + "------tenant ----" + input3 + "------platform ----" + input4 + "--------plan ----" + input5)    

        # Determine the selected option in Input 3
        if input4 == "GCP":
            api_url = str('https://'+ input1 + gcp + gcp_plan + input5 + total)
        elif input4 == "HANA":
            api_url = str('https://' + input1 + legacy + plan + input5)
        elif input4 == "Oracle":
            api_url = str('https://' + input1 + legacy + plan + input5 + total)

        try:
            # Make an API request to fetch data
            files_remove()
            print(api_url)
            #headers = {'authorization': "Basic %s" % b64Val, 'cache-control': "no-cache",     'Content-Type': "application/json"}
            #response = requests.post(api_url, headers=headers)
            #print(response.json)

            # data_list = []
            # # Loop through each row in the DataFrame
            # for index, row in df.iterrows():
            #     data_dict = row.to_dict()
            #     data_list.append(data_dict)
            #     print(data_list)

            headers = {'authorization': "Basic %s" % b64Val, 'cache-control': "no-cache", 'Content-Type': "application/json"}
            response = requests.post(api_url, headers=headers, data=data_list)
            #print(response.status_code)
            #print(response.text)
            if response.status_code == 201:
                data = response.json()
                json_str = json.dumps(data[input5])
                error_data  = json.loads(json_str)
                print(json_str)
                if input5 in data:
                    success_count = sum('dataTypeSeq' in record for record in data[input5])
                    print(f"Count of dataTypeSeq: {success_count}")
            elif response.status_code == 207:
                data = response.json()
                json_str = json.dumps(data[input5])      
                print(json_str)          
                error_data  = json.loads(json_str)
                #success_count += 1

                error_messages = []
                for index, error in enumerate(error_data):
                    if '_ERROR_' in error:
                        error_message = error['_ERROR_']
                        error_messages.append({'Row': index + 1, 'Error Message': error_message})
                
                    # Check if the 'dataTypeSeq' key exists in the response
                if input5 in data:
                    success_count = sum('dataTypeSeq' in record for record in data[input5])
                    print(f"Count of dataTypeSeq: {success_count}")
                            
            elif response.status_code == 400:
                data = response.json()
                json_str = json.dumps(data[input5])
                error_data  = json.loads(json_str)
                #print(error_data )
                
                error_messages = []
                for index, error in enumerate(error_data):
                    if '_ERROR_' in error:
                        error_message = error['_ERROR_']
                        error_messages.append({'Row': index + 1, 'Error Message': error_message})
                print(error_messages)
            elif response.status_code == 500:
                success_count += 1                              
            else:
                error_messages = ["Error parsing response"]

            error_details = error_messages
            error_count = len(error_details)

            #print(error_details)
            print(f"error count ----->{error_count}")
            print(success_count)
        except requests.exceptions.RequestException as e:
            print(e)
            error_details.append({
                'Row': 0,  # You may want to adjust this value based on your needs
                'Error Message': str(e)
            })
            print("API request failed:", e)
            response.raise_for_status()

    return render_template('import.html', data=error_details, success_count=success_count, error_count=error_count)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(cf_port), debug=True)


# , 