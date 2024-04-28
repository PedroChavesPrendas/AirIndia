import sys
import os
import requests
from bs4 import BeautifulSoup
from s3 import upload_s3
import psycopg2
from dotenv import load_dotenv
load_dotenv()
import boto3
import json
import hashlib
sys.path.append('../utils')
from log import get_logger
from sentry import sentry_sdk
logger = get_logger()

MAX_RETRY = 3

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

AWS_ACCESS = os.getenv('AWS_ACCESS')
AWS_SECRET = os.getenv('AWS_SECRET')
AWS_REGION = os.getenv('AWS_REGION')

AIRLINE_ENGINE_SCRAPER_OUTPUT_Q = os.getenv('AIRLINE_ENGINE_SCRAPER_OUTPUT_Q')
sqs_client = boto3.client('sqs', aws_access_key_id=AWS_ACCESS,
                          aws_secret_access_key=AWS_SECRET, region_name=AWS_REGION)

def login(username, password, retry=0):
    """
    Login to the server and return the session object.
    """
    try:
        session = requests.Session()
        req = session.get('https://mdi.megasoftsol.com/MDI/AFGST/login.aspx?cmp=ACGST')
        soup = BeautifulSoup(req.text, 'html.parser')

        # Get the hidden fields
        hidden_fields = soup.find_all('input', type='hidden')
        
        # Create a dictionary of the hidden fields
        hidden_fields_dict = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
        }
        for field in hidden_fields:
            hidden_fields_dict[field['name']] = field.get('value', '')

        req = session.post('https://mdi.megasoftsol.com/MDI/AFGST/login.aspx?cmp=ACGST', data={
            **hidden_fields_dict,
            'ucLogin$txtUserID': username,
            'ucLogin$txtUserPWD': '********************',
            'ucLogin$hfUserPWD': password,
            'ucLogin$btnLogin': 'Login',
        }, allow_redirects=True)

        if req.history:
            return session
        else:
            soup = BeautifulSoup(req.text, 'html.parser')
            invalid_login_element = soup.find('span', {'id': 'ucLogin_cvLogin'})

            if invalid_login_element and 'Invalid Login Credentials!' or 'Your User ID has been locked.' in invalid_login_element.text:
                logger.info(f"{invalid_login_element.text}")
            return None
    except:
        if retry<MAX_RETRY:
            return login(username, password, retry+1)
        else:
            logger.info("Could not get session for logging into Air Canada GST portal after exceeding maximum retry attempts")
         
    
def get_data(username,password):            
    try:
        session = login(username, password)

        if not session:
            return None
        
        req = session.get('https://mdi.megasoftsol.com/MDI/Home.aspx')
        soup = BeautifulSoup(req.text, 'html.parser')

        link_to_page = f"https://mdi.megasoftsol.com/MDI/{soup.find('a', string='Manage Invoices')['href']}"
        req = session.get(link_to_page)
        soup = BeautifulSoup(req.text, 'html.parser')

        # Get the hidden fields
        hidden_fields = soup.find_all('input', type='hidden')

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
        }

        for field in hidden_fields:
            hidden_fields_dict[field['name']] = field.get('value', '')

        req = session.post(link_to_page, data=hidden_fields_dict, headers={
            'user-agent': 'Chrome/102.0.5005.99 Safari/537.36',
        })
        soup = BeautifulSoup(req.text, 'html.parser')

        table = soup.find('table', {'class': 'hui-table-theme'})
        body = [tr for tr in table.find_all("tr")[1:]]

        for row in body:
            row_text = [td.text.strip() for td in row.find_all("td")]
            filename= row_text[6]
            file_url = row.find('a')['href']    

            try:
                req = session.get(f"https://mdi.megasoftsol.com/MDI/{file_url}", stream=True, timeout=(1,1))
            except (requests.ConnectTimeout, requests.ReadTimeout):
                logger.info(f"A connection/readtimeout exception occured while fetching the {str(filename)} invoice")
                continue
            
            with open(filename, 'wb') as f:
                for chunk in req.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        f.flush()

            status, s3_link = upload_s3(f'{filename}', filename, 'aircanada')
            if status:
                id = hashlib.sha256((row_text[3]+row_text[4]+row_text[6]).encode('utf-8')).hexdigest()
                data_to_write ={"id":id, "document_id" :row_text[3], "document_type" :row_text[4], "description" :row_text[5], "file":row_text[6], "uploaded_by":row_text[7], "uploaded_by":row_text[8], "s3_link":s3_link}
                try:
                    # Execute the INSERT query
                    with conn, conn.cursor() as cursor:
                        # Construct the INSERT query
                        insert_query = """
                            INSERT INTO airline_engine_scraper_aircanada
                            (id, document_id, document_type, description, file, uploaded_by, s3_link)
                            VALUES (%(id)s, %(document_id)s, %(document_type)s, %(description)s, %(file)s, %(uploaded_by)s, %(s3_link)s)
                            ON CONFLICT DO NOTHING;
                        """
                        # Execute the INSERT query with the sample data
                        cursor.execute(insert_query, data_to_write)
                        # Commit the transaction
                        conn.commit()
                        logger.info("airline_engine_scraper_aircanada successfully updated with required datavalues")
                        message={
                            "source":"LOGIN_SCRAPER",
                            "success": True,
                            "message": "FILES_PUSHED_TO_S3",
                            "guid":None,
                            "data": {'s3_link': [s3_link], 'airline':'aircanada'}
                        }
                        os.remove(filename)

                        # Send message to Q for parsing.
                        sqs_client.send_message(
                            QueueUrl=AIRLINE_ENGINE_SCRAPER_OUTPUT_Q,
                            MessageBody=json.dumps(message)
                        )
                except Exception as e:
                    logger.info(f"Error inserting data into PostgreSQL:, {str(e)}")
                    
    except Exception as e:
        logger.info(f"An exception occured while logging in to Air Canada GST portal, {str(e)}")       


def main(args):
    if len(args) != 3:
        logger.info("Not all arguments provided for logging in to the  Air Canada GST portal")
    else:
        username = args[1]
        password = args[2]
        get_data(username, password)

if __name__ == "__main__":
    main(sys.argv)
