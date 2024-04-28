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

postgres_host = os.getenv("POSTGRES_HOST")
postgres_db = os.getenv("POSTGRES_DB")
postgres_user = os.getenv("POSTGRES_USER")
postgres_password = os.getenv("POSTGRES_PASS")

conn = psycopg2.connect(
    host=postgres_host,
    database=postgres_db,
    user=postgres_user,
    password=postgres_password
)

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

    response = requests.post('https://api.lhgroupgst.com/api/Account/Login', json={
        'Email': f"{code}_{username}",
        'Password': password,
        'RememberMe': False,
        'IpAddress': '0.0.0.0'
    })

    try:
        if response.status_code == 200 and response.json()['payload']['message'] == 'Success':
            data = response.json()
            return {
                'user_id': data['payload']['userId'],
                'customer_id': data['payload']['custId'],
                'access_token': data['payload']['accessToken']
            }
        else:
            return response.json()['payload']['message']

    except Exception as e:
        return 'Failed to login: Credentials are incorrect'


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

            zipfile_obj = zipfile.ZipFile(io.BytesIO(res.content))
            for filename in zipfile_obj.namelist():
                # read the file contents as bytes
                file_data = zipfile_obj.read(filename)
                file_list = [os.path.abspath(f) for f in os.listdir()]
               
                with open(f'scrapers/temp/{filename}', 'wb') as f:
                    f.write(file_data)

                status, s3_link = upload_s3(f'scrapers/temp/{filename}', filename, airline)
                if status:
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
            print("Failed to get the file")
    except Exception as e:
        print("Exception while scraping",str(e))


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
                        INSERT INTO airline_engine_scraper_lufthansa_klm_austrian_brussels
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
    

def main(args):
    if len(args) < 3:
        print("No Arguments Provided")
    else:
        code = args[1]
        username = args[2]
        password = args[3]
        from_date = args[4]
        to_date = args[5]
        creds = login(code, username, password)
        if type(creds) == dict:
            scrape_data(creds, from_date, to_date)
            
if __name__ == "__main__":
    main(sys.argv)