from datetime import datetime
import sys
import requests
import zipfile
import io
import os
import json
from s3 import upload_s3
import psycopg2
import boto3
import hashlib
from utils.pg import conn
from utils.log import get_logger
import csv 
logger = get_logger()
cookie = None
requestToken = None
AWS_ACCESS = os.getenv('AWS_ACCESS')
AWS_SECRET = os.getenv('AWS_SECRET')
AWS_REGION = os.getenv('AWS_REGION')
AIRLINE_ENGINE_SCRAPER_OUTPUT_Q = os.getenv('AIRLINE_ENGINE_SCRAPER_OUTPUT_Q')
sqs_client = boto3.client('sqs', aws_access_key_id=AWS_ACCESS,
                          aws_secret_access_key=AWS_SECRET, region_name=AWS_REGION)
AIRLINE_IDS = {
    'LH': 8,
    'SW': 9,
}
def login(code, username, password):
    logger.info(f"Logging in for {username, password}")
    response = requests.post('https://api.lhgroupgst.com/api/Account/Login', json={
        'Email': f"{code}_{username}",
        'Password': password,
        'RememberMe': False,
        'IpAddress': '0.0.0.0'
    })
    print(response.json()['payload'])
    try:
        if response.status_code == 200 and response.json()['payload']['message'] == 'Success':
            data = response.json()
            return {
                'status': True,
                'user_id': data['payload']['userId'],
                'customer_id': data['payload']['custId'],
                'access_token': data['payload']['accessToken']
            }
        else:
            logger.info(f"Failed to login: Invalid response {response.json()['payload']['message']}")
            return {
            "status": False,
            "response" : response.json()['payload']['message']
            }
    except Exception as e:
        logger.exception('Failed to login: Credentials are incorrect')
        return {
            "status": False,
            "response" : f"Exception :: {e}"
            }
def get_zip(creds, info_ids, airline):
    response = requests.post('https://api.lhgroupgst.com/api/GstInfo/GstPDFDownload_New', json={
        'AirlineCode': airline,
        'UserId': creds['user_id'],
        'infoId': info_ids,
    }, headers={
        'Authorization': f'Bearer {creds["access_token"]}',
        'Content-Type': 'application/json'
    })
    payload = json.loads(response.json()['payload'])
    download_url = payload['downloadurl']
    try:
        if response.status_code == 200 and download_url.endswith('.zip'):
            res = requests.get(download_url, stream=True)
            print("response", res)
            if res.status_code == 200: 
                zipfile_obj = zipfile.ZipFile(io.BytesIO(res.content))
            else:
                print(f"HTTP Error {res.status_code}: {res.text}")
                return
            # zipfile_obj = zipfile.ZipFile(io.BytesIO(res.content))
            logger.info(f"got files :: {len(zipfile_obj.namelist())}")
            for filename in zipfile_obj.namelist():
                # read the file contents as bytes
                file_data = zipfile_obj.read(filename)
                file_list = [os.path.abspath(f) for f in os.listdir()]
                with open(f'scrapers/temp/{filename}', 'wb') as f:
                    f.write(file_data)
                status, s3_link = upload_s3(f'scrapers/temp/{filename}', filename, airline)
                if status:
                    logger.info("FILE UPLOADED TO S3")
                    message={
                            "source":"LOGIN_SCRAPER",
                            "success": True,
                            "message": "FILES_PUSHED_TO_S3",
                            "guid": None,
                            "data": {'s3_link': [s3_link], 'airline':airline}
                            }
                    sqs_client.send_message(
                        QueueUrl=AIRLINE_ENGINE_SCRAPER_OUTPUT_Q,
                        MessageBody=json.dumps(message)
                    )
                os.remove(f'scrapers/temp/{filename}')
        else:
            logger.info("Failed to get the file")
    except Exception as e:
        logger.exception("Exception while scraping",str(e))
def scrape_data(creds, from_date, to_date):
    response = requests.post(
        'https://api.lhgroupgst.com/api/GstInfo/GetGstInfoAllData',
        headers={
            'Authorization': f'Bearer {creds["access_token"]}',
            'Content-Type': 'application/json'
        },
        json={
            "UserId": creds['user_id'],
            "AirlineCode": "LH",
            "TransactionType": 0,
            "TicketNo": "",
            "PNRNo": "",
            "PassengerName": "",
            "CustomerGSTNo": "",
            "FromTransDate": from_date,
            "ToTransDate": to_date,
            "AirlineId": 0,
            "CustId": creds['customer_id'],
        }
    )
    lh_data = response.json()['payload']
    response = requests.post(
        'https://api.lhgroupgst.com/api/GstInfo/GetGstInfoAllData',
        headers={
            'Authorization': f'Bearer {creds["access_token"]}',
            'Content-Type': 'application/json'
        }, json={
            "UserId": creds['user_id'],
            "AirlineCode": "LX",
            "TransactionType": 0,
            "TicketNo": "",
            "PNRNo": "",
            "PassengerName": "",
            "CustomerGSTNo": "",
            "FromTransDate": from_date,
            "ToTransDate": to_date,
            "AirlineId": 0,
            "CustId": creds['customer_id'],
        }
    )
    sw_data = response.json()['payload']
    response = requests.post(
        'https://api.lhgroupgst.com/api/GstInfo/GetGstInfoAllData',
        headers={
            'Authorization': f'Bearer {creds["access_token"]}',
            'Content-Type': 'application/json'
        }, json={
            "UserId": creds['user_id'],
            "AirlineCode": "AU",
            "TransactionType": 0,
            "TicketNo": "",
            "PNRNo": "",
            "PassengerName": "",
            "CustomerGSTNo": "",
            "FromTransDate": from_date,
            "ToTransDate": to_date,
            "AirlineId": 0,
            "CustId": creds['customer_id'],
        }
    )
    au_data = response.json()['payload']
    response = requests.post(
        'https://api.lhgroupgst.com/api/GstInfo/GetGstInfoAllData',
        headers={
            'Authorization': f'Bearer {creds["access_token"]}',
            'Content-Type': 'application/json'
        }, json={
            "UserId": creds['user_id'],
            "AirlineCode": "BR",
            "TransactionType": 0,
            "TicketNo": "",
            "PNRNo": "",
            "PassengerName": "",
            "CustomerGSTNo": "",
            "FromTransDate": from_date,
            "ToTransDate": to_date,
            "AirlineId": 0,
            "CustId": creds['customer_id'],
        }
    )
    br_data = response.json()['payload']
    print(lh_data)
    if len(lh_data) == 0 and len(sw_data) == 0 and len(au_data) == 0 and len(br_data) == 0:
        return []
    else:
        all_data = lh_data + sw_data + au_data + br_data
        for leteachrow in all_data:
            formated_doi = datetime.strptime(leteachrow['doi'], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d")
            formated_trans_date = datetime.strptime(leteachrow['transDate'], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d")
            id = hashlib.sha256((str(leteachrow['infoId'])+leteachrow['airlineCode']+str(leteachrow['ticketNo'])).encode('utf-8')).hexdigest()
            data_to_write ={"id":id, "info_id" :leteachrow['infoId'], "airline_code" :leteachrow['airlineCode'], "ticket_no" :leteachrow['ticketNo'], "doi" :formated_doi, "iata_code":leteachrow['iataCode'], "pnr_no":leteachrow['pnrNo'], "transaction_type":leteachrow['transactionType'], "trans_type":leteachrow['transType'], "trans_no":leteachrow['transNo'], "trans_date":formated_trans_date, "airline_gst_no":leteachrow['airlineGSTNo'], "customer_gst_no":leteachrow['customerGSTNo'], "customer_name":leteachrow['customerName'], "email":leteachrow['email'], "phone_no":leteachrow['phoneNo'], "passenger_name":leteachrow['passengerName'], "taxable_amt":leteachrow['taxableAmt'], "gst_amt":leteachrow['gstAmt'], "total_amt":leteachrow['totalAmt']}
            try:
                # Execute the INSERT query
                with conn, conn.cursor() as cursor:
                    # Construct the INSERT query
                    insert_query = """
                        INSERT INTO airline_engine_scraper_lh_sw_au_br
                        (id, info_id, airline_code, ticket_no, doi, iata_code, pnr_no, transaction_type, trans_type, trans_no, trans_date, airline_gst_no, customer_gst_no, customer_name, email, phone_no, passenger_name, taxable_amt, gst_amt, total_amt)
                        VALUES (%(id)s, %(info_id)s, %(airline_code)s, %(ticket_no)s, %(doi)s, %(iata_code)s, %(pnr_no)s, %(transaction_type)s, %(trans_type)s, %(trans_no)s, %(trans_date)s, %(airline_gst_no)s, %(customer_gst_no)s, %(customer_name)s, %(email)s, %(phone_no)s, %(passenger_name)s, %(taxable_amt)s, %(gst_amt)s, %(total_amt)s);
                    """
                    # Execute the INSERT query with the sample data
                    cursor.execute(insert_query, data_to_write)
                    # Commit the transaction
                    conn.commit()
            except Exception as e:
                    print("Error inserting data into PostgreSQL:", e)
        get_zip(creds,[x['infoId'] for x in lh_data],'lufthansa')
        get_zip(creds,[x['infoId'] for x in sw_data],'swiss')
        get_zip(creds,[x['infoId'] for x in au_data],'austrian')
        get_zip(creds,[x['infoId'] for x in br_data],'brussels')
def get_lh_swiss_data(code, username, password, from_date, to_date ):
    creds = login(code, username, password)
    logger.info(creds)
    if creds['status'] == True:
        logger.info("Succesfully logged in")
        scrape_data(creds, from_date, to_date)
        return True, 5
    else:
        return False, 0
def main():
    code = "RI78"
    username = "Admin"
    password = "unjnD647"
    from_date = "2023-03-01"
    to_date = "2024-03-10"
    creds = login(code, username, password)
    print("creds", creds)
    if type(creds) == dict:
        scrape_data(creds, from_date, to_date)

main()

# def main(code, password):
#     code,
#     username = "Admin"
#     password,
#     from_date = "2024-01-01"
#     to_date = "2024-01-16"
#     creds = login(code, username, password)
#     if type(creds) == dict:
#         scrape_data(creds, from_date, to_date)

# def read_credentials_and_run():
#     with open('lufthansa_creds.csv', 'r') as csvfile:
#         csvreader = csv.reader(csvfile)
#         # next(csvreader) 
#         for row in csvreader:
#             portal_pass, code = row
#             main(code, portal_pass)

# read_credentials_and_run()

