import sys
import os
import requests
from bs4 import BeautifulSoup
import psycopg2
from dotenv import load_dotenv
load_dotenv()
import boto3
import json
import hashlib
from utils.log import get_logger
from utils.pg import conn
import tempfile
import csv 

os.makedirs('scrapers/temp',exist_ok=True)
logger = get_logger()
from s3 import upload_s3
AWS_ACCESS = os.getenv('AWS_ACCESS')
AWS_SECRET = os.getenv('AWS_SECRET')
AWS_REGION = os.getenv('AWS_REGION')
AIRLINE_ENGINE_SCRAPER_OUTPUT_Q = os.getenv('AIRLINE_ENGINE_SCRAPER_OUTPUT_Q')
sqs_client = boto3.client('sqs', aws_access_key_id=AWS_ACCESS,
                          aws_secret_access_key=AWS_SECRET, region_name=AWS_REGION)
def login(username, password):
    """
    Login to the server and return the session object.
    """
    session = requests.Session()
    req = session.get('https://mdi.megasoftsol.com/MDI/AFGST/Login.aspx?CID=AFGST&NU=1')
    soup = BeautifulSoup(req.text, 'html.parser')
    logger.info(f"Getting data for user {username} & {password}")
    # Get the hidden fields
    hidden_fields = soup.find_all('input', type='hidden')
    # Create a dictionary of the hidden fields
    hidden_fields_dict = {
        '__EVENTTARGET': '',
        '__EVENTARGUMENT': '',
    }
    for field in hidden_fields:
        hidden_fields_dict[field['name']] = field.get('value', '')
    req = session.post('https://mdi.megasoftsol.com/MDI/AFGST/Login.aspx?CID=AFGST&NU=1', data={
        **hidden_fields_dict,
        'ucLogin$txtUserID': username,
        'ucLogin$txtUserPWD': '********************',
        'ucLogin$hfUserPWD': password,
        'ucLogin$btnLogin': 'Login',
    }, allow_redirects=True)
    if req.history:
        return session
    else:
        return None
def get_airfrance_data(username,password, retry=0):
    """
    Get the data from the server.
    """
    try:
        session = login(username, password)
    except Exception:
        return False, 0
    if not session:
        if retry < 3:
            return get_airfrance_data(username, password, retry=retry+1)
        else:
            return False, 0
    try:
        req = session.get('https://mdi.megasoftsol.com/MDI/Home.aspx')
        soup = BeautifulSoup(req.text, 'html.parser')
        link_to_page = f"https://mdi.megasoftsol.com/MDI/{soup.find('a', string='Manage Invoices')['href']}"
        req = session.get(link_to_page)
        soup = BeautifulSoup(req.text, 'html.parser')
        # Get the hidden fields
        hidden_fields = soup.find_all('input', type='hidden')
        # Create a dictionary of the hidden fields
        hidden_fields_dict = {
            'ctl00$scrpManager': 'ctl00$scrpManager|ctl00$MiddleContent$gvRep$ctl23$gvPager$ddlPageSize',
            '__EVENTTARGET': 'ctl00$MiddleContent$gvRep$ctl23$gvPager$ddlPageSize',
            '__EVENTARGUMENT': '',
            'ctl00$MiddleContent$gvRep$ctl23$gvPager$ddlPageSize': 'All',
            'ctl00$MiddleContent$gvRep$ctl23$gvPager$txtGoToPage': '1',
            '__ASYNCPOST': 'true',
            '__LASTFOCUS': '',
            'tvwMenu_ExpandState': 'n',
            'tvwMenu_SelectedNode': 'tvwMenut0',
            'tvwMenu_PopulateLog': '',
            'ctl00$MiddleContent$txtSearch': '',
            'ctl00$MiddleContent$ddlDocCodeF': '',
            'ctl00$MiddleContent$ddlDocCode': '',
            'ctl00$MiddleContent$ucEmailMessage$txtTo': '',
            'ctl00$MiddleContent$txtDocTagsF': '',
            'ctl00$MiddleContent$txtDocRefNo': '',
            'ctl00$MiddleContent$txtDocRefNoF': '',
            'ctl00$MiddleContent$ucEmailMessage$txtMessage': '',
            'ctl00$MiddleContent$ucEmailMessage$txtBCC': '',
            'ctl00$MiddleContent$ucEmailMessage$txtSubject': '',
            'ctl00$MiddleContent$ucEmailMessage$txtFrom': '',
            'ctl00$MiddleContent$txtDocDesc': '',
            'ctl00$MiddleContent$ucEmailMessage$txtCC': '',
            'ctl00$MiddleContent$txtDocDescF': '',
            'ctl00$MiddleContent$txtDocTags': '',
            'ctl00$MiddleContent$ucEmailMessage$hfAttachments': '',
            "": ""
        }
        for field in hidden_fields:
            hidden_fields_dict[field['name']] = field.get('value', '')
        req = session.post(link_to_page, data=hidden_fields_dict, headers={
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.99 Safari/537.36',
        })
        soup = BeautifulSoup(req.text, 'html.parser')
        table = soup.find('table', {'class': 'hui-table-theme'})
        body = [tr for tr in table.find_all("tr")[1:]]
        #Logging records found
        logger.info(f"Found {len(body)} Records")
        for row in body:
            row_text = [td.text.strip() for td in row.find_all("td")]
            file_url = row.find('a')['href']
            try:
                req = session.get(f"https://mdi.megasoftsol.com/MDI/{file_url}", stream=True, timeout=(2,2))
            except (requests.ConnectTimeout, requests.ReadTimeout):
                continue
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(req.content)
                status, s3_link = upload_s3(f.name, row_text[6], 'airfrance')
                if status:
                    id = hashlib.sha256((row_text[3]+row_text[4]+row_text[6]).encode('utf-8')).hexdigest()
                    data_to_write ={"id":id, "document_id" :row_text[3], "document_type" :row_text[4], "description" :row_text[5], "file":row_text[6], "uploaded_by":row_text[7], "uploaded_by":row_text[8], "s3_link":s3_link}
                    try:
                        # Execute the INSERT query
                        with conn, conn.cursor() as cursor:
                            # Construct the INSERT query
                            insert_query = """
                                INSERT INTO airline_engine_scraper_airfrance
                                (id, document_id, document_type, description, file, uploaded_by, s3_link)
                                VALUES (%(id)s, %(document_id)s, %(document_type)s, %(description)s, %(file)s, %(uploaded_by)s, %(s3_link)s);
                            """
                            # Execute the INSERT query with the sample data
                            cursor.execute(insert_query, data_to_write)
                            # Commit the transaction
                            conn.commit()
                    except Exception as e:
                        logger.exception("Error inserting data into PostgreSQL:", e)
                    finally:
                        message={
                                "source":"LOGIN_SCRAPER",
                                "success": True,
                                "message": "FILES_PUSHED_TO_S3",
                                "guid":None,
                                "data": {'s3_link': [s3_link], 'airline':'airfrance'}
                            }
                        sqs_client.send_message(
                            QueueUrl=AIRLINE_ENGINE_SCRAPER_OUTPUT_Q,
                            MessageBody=json.dumps(message)
                        )
        return True, len(body)
    except Exception as e:
        logger.exception(f"Got an exception scraping user :: {username}")
        if retry < 3:
            logger.info("Retrying scrape attempt")
            return get_airfrance_data(username, password, retry=retry+1)
        else:
            logger.info("Failed to scrape")
            return True, 0
def main(args):
    if len(args) == 1:
        print("No Arguments Provided")
    else:
        username = args[1]
        password = args[2]
        get_airfrance_data(username, password)
if __name__ == "__main__":
    main(sys.argv)

def main(username):
    username = "AAACC0457C"
    password = "AAACC0457C"
    get_airfrance_data(username, password)

main('AAACC0457C')

# def main(username):
#     # username = "AACCA6398Q"
#     # password = "AACCA6398Q"
#     get_airfrance_data(username, username)

# def read_credentials_and_run():
#     with open('af_pass.csv', 'r') as csvfile:
#         csvreader = csv.reader(csvfile)
#         next(csvreader) 
#         for row in csvreader:
#             username = row
#             main(username)

# read_credentials_and_run()