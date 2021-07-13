import requests
from requests.auth import HTTPBasicAuth
import pandas 
import datetime
import json
import os
import hvac
from google.cloud import secretmanager
def pull_bamboo_secrets():
    current_env = os.environ['WIZELAKE_ENV']
    gc_secrets_client = secretmanager.SecretManagerServiceClient()
    project_id = os.environ['PROJECT_ID']
    vault_url_name = f"projects/{project_id}/secrets/wizelake-vault-url/versions/latest"
    vault_role_name = f"projects/{project_id}/secrets/wizelake-vault-role-id/versions/latest"
    vault_secret_name = f"projects/{project_id}/secrets/wizelake-vault-secret-id/versions/latest"
    wizelake_vault_url = gc_secrets_client.access_secret_version(request={"name": vault_url_name}).payload.data.decode("UTF-8")
    wizelake_role_id = gc_secrets_client.access_secret_version(request={"name": vault_role_name}).payload.data.decode("UTF-8")
    wizelake_secret_id = gc_secrets_client.access_secret_version(request={"name": vault_secret_name}).payload.data.decode("UTF-8")
    wizelake_role_id = gc_secrets_client.access_secret_version(request={"name": vault_role_name}).payload.data.decode("UTF-8")
    print(type(wizelake_role_id), wizelake_role_id)
    vault_client = hvac.Client(url=wizelake_vault_url)
    vault_client.auth.approle.login(
        role_id=wizelake_role_id,
        secret_id=wizelake_secret_id,
    )
    print('Is Authenticaded?', vault_client.is_authenticated())
    secret_version_response = vault_client.secrets.kv.v2.read_secret_version(
        mount_point='wizelake',
        path = f'{current_env}/bamboo/config'
    )
    bamboo_api_key = secret_version_response['data']['data']['prod-api-key']
    bamboo_api_password = secret_version_response['data']['data']['api-password']
    bamboo_fetch_url = secret_version_response['data']['data']['fetch-url']
    secrets = {
        "FETCH_URL": bamboo_fetch_url,
        "API_USER": bamboo_api_key,
        "API_PASSWORD": bamboo_api_password
    }
    return secrets
def fetch_bamboo_data(endpoint, options):
    #config = pull_bamboo_secrets()
    config = {
        "FETCH_URL": "https://api.bamboohr.com/api/gateway.php/wizelinetestaccount/v1/",
        "API_USER": "86e8bc857ab716d57ed36b7cfaa139b9e2ef2f4d",
        "API_PASSWORD": "x"
    }
    basic_auth = HTTPBasicAuth(
        config['API_USER'], config['API_PASSWORD']
    )
    response = requests.get(
        config['FETCH_URL'] + endpoint,
        params=options,
        auth= basic_auth,
        headers={ 'Accept': 'application/json' }
    )
    print(response)
    response.encoding = 'utf-8'
    return response.json() if response else {}
def getReport(id):
    options = {'format': 'JSON', 'fd':'yes', 'onlyCurrent': 'false'}
    return fetch_bamboo_data(f'reports/{id}', options)
def process_bamboo_report(id):
    report_data = getReport(id)
    # Define columns order according to the employees fields
    fields_order = list(report_data["employees"][0].keys())
    # Generate bigQuery schema
    schema_local_file_name, schema = generate_bamboo_bigQuery_schema(fields_order, report_data["fields"])
    # Parse and write csv
    local_csv_name = bamboo_report_to_csv(schema, report_data["employees"], id)
    # Get the target GCS file names for both csv and json files
    # The source (bamboo in this case) would change according to the DAG
    remote_csv_name, schema_remote_file_name = get_remote_file_names("snapshots/bamboo-new-integration", local_csv_name, schema_local_file_name)
    return schema_local_file_name, schema_remote_file_name, local_csv_name, remote_csv_name
def bamboo_report_to_csv(schema, employees, report_id):
    rows = []
    headers = []
    for field in schema:
        headers.append(field["name"])
    # Each employee will correspond to a row in the csv file 
    for employee in employees:
        row = []
        for value in employee.values():
            # Catching invalid dates coming from Bamboo response
            # In order to prevent an error when loading to BigQuery (unable to parse string to date)
            if value == "0000-00-00":
                row.append("")
            else:
                row.append(value)
        rows.append(row)
    # todo: remove absolute path to file
    file_name = f"bamboo_report_{report_id}.csv"
    df = pandas.DataFrame(rows, columns=headers)
    df.to_csv(file_name, sep=',', encoding='utf-8', index=False)
    return file_name
def generate_bamboo_bigQuery_schema(fields_order, fields):
    data_types = {
        "employee_number": "INT64",
        "date": "DATE",
    }
    # Adding the bamboo id as the first element of the schema
    # since it is not provided as a field in the list of fields contained in the report
    schema = [ {"name": "id", "type": "INT64", "mode": "REQUIRED"} ]
    known_fields = {
        "4419.0": "compensationEffectiveDate",
        "4410.0": "jobEffectiveDate",
        "4503.0": "billable",
        "4414.0": "countryDate",
        "91": "reportingTo",
    }
    for field in fields:
        new_name = ""
        if field["id"] in known_fields:
            new_name = known_fields[field["id"]]
        elif field["id"].isdigit() or field["id"].replace(".", "", 1).isdigit():
           new_name = (field["name"][0].lower() + field["name"][1:]).replace(" ", "").replace(":", "") 
        else:
            new_name = field["id"]
        if field["type"] in data_types:
            new_type = data_types[field["type"]]
        else:
            new_type = "STRING"
        schema_field = {"name": new_name, "type": new_type, "mode": "NULLABLE"}
        schema.insert(fields_order.index(field["id"]), schema_field)
    # todo: remove full path definition to save file
    schema_file_name = 'employees_schema.json'
    with open(schema_file_name, 'w', encoding='utf-8') as f:
        json.dump(schema, f, ensure_ascii=False, indent=4)
    return (schema_file_name, schema)
def get_remote_file_names(source, csv_name, json_name):
    date = datetime.datetime.now()
    # todo: fix removal of last / due to csv and json name
    new_csv_name = f"{source}/{date.month}/{date.day}/{csv_name}"
    new_json_name = f"{source}/{date.month}/{date.day}/{json_name}"
    return new_csv_name, new_json_name