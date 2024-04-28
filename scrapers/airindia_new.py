import requests
import imaplib
from bs4 import BeautifulSoup
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import concurrent.futures
import sys
from s3 import upload_s3
import psycopg2
import hashlib
import boto3
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
import time


postgres_host = os.getenv("POSTGRES_HOST")
postgres_db = os.getenv("POSTGRES_DB")
postgres_user = os.getenv("POSTGRES_USER")
postgres_password = os.getenv("POSTGRES_PASS")
port = os.getenv("POSTGRES_PORT")

conn = psycopg2.connect(
    host=postgres_host,
    database=postgres_db,
    user=postgres_user,
    password=postgres_password,
    port=port
)

cookie = None
requestToken = None

# Get the current date
current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

client_name = 'testmachinsey27march'  # Enter client name here every time

# Create the directory path based on the current date
directory_path = f'{client_name}_{current_datetime}'
if not os.path.exists(directory_path):
    os.makedirs(directory_path)

AWS_ACCESS = os.getenv('AWS_ACCESS')
AWS_SECRET = os.getenv('AWS_SECRET')
AWS_REGION = os.getenv('AWS_REGION')

AIRLINE_ENGINE_SCRAPER_OUTPUT_Q = os.getenv('AIRLINE_ENGINE_SCRAPER_OUTPUT_Q')
sqs_client = boto3.client('sqs', aws_access_key_id=AWS_ACCESS,
                          aws_secret_access_key=AWS_SECRET, region_name=AWS_REGION)

def _web_driver():
    options = webdriver.ChromeOptions()
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "directory_upgrade": True
    }
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ['enable-automation'])
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--window-size=1920,1400")
    options.add_argument('--disable-gpu')
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.implicitly_wait(1)
    return driver

def otp_handler(mail: imaplib.IMAP4_SSL,ref):
    mail.select("inbox")
    while True:
        _, data = mail.search(None, 'BODY "Reference No is '+ref.replace(' ','').replace('\' \'"]','')+'."')
        if data:
            mail_data = mail.fetch(data[0], '(RFC822)')
            soup = BeautifulSoup(mail_data[1][0][1], 'html.parser')
            otp = soup.find('b').text
            ref_num = soup.find('b').text
            print("Got OTP ",otp)
            return otp
        else:
            continue

def login(driver,email, password):
    print("-"*20+'INITIATING LOGIN'+20*"-")
    driver.get('https://gst-ai.accelya.io/gstportal/home.htm')
    driver.save_screenshot('login.png')
    driver.delete_all_cookies()
    driver.execute_script('window.localStorage.clear()')
    driver.execute_script('window.sessionStorage.clear()')
    time.sleep(4)
    driver.find_element(By.XPATH,'//*[@id="userName"]').send_keys(email)
    driver.find_element(By.XPATH,'//*[@id="password"]').send_keys(password)
    driver.find_element(By.ID,'loginForm_login').click()
    print("Login Clicked")
    driver.save_screenshot('login.png')
    
    try:
        driver.find_element(By.ID,'sessionConfirmAlertForm_sessionYesButton').click()
        print("Another Session Found and Killed")
        time.sleep(1)
        print("Trying Relogin")
        return login(driver,email, password)
    except:
        print("No Other Session Found")
        pass

    # Wait for the element to be present
    wait = WebDriverWait(driver, 10)
    element = wait.until(EC.presence_of_element_located((By.ID, 'otpRefSpan_multiFactorAuth')))

    # Once the element is found, you can get its text
    ref = element.text
    print("OTP Ref ",ref)
    time.sleep(30)
    button = driver.find_element(By.XPATH,"//button[@name='submitOTP']")
    driver.execute_script("arguments[0].disabled = false;", button)
    driver.save_screenshot('login.png')
    max_retries = 5  # Maximum number of OTP retrieval retries
    while max_retries > 0:
        try:
            otp = input("Enter OTP:")
            driver.find_element(By.XPATH, "//input[@name='otpField_multiFactorAuth']").send_keys(otp)
            driver.find_element(By.XPATH, "//button[@name='submitOTP']").click()
            print("OTP Submitted")
            # driver.save_screenshot('login.png')
            time.sleep(5)
            driver.save_screenshot('login.png')
            break  # Break out of the loop if OTP submission is successful
        except Exception as e:
            print("OTP Error:", str(e))
            max_retries -= 1
            if max_retries == 0:
                return ('error', 'otp error')
            else:
                print(f"Retrying... {max_retries} retries left")
                time.sleep(2)  # Add a small delay before retrying
    

def get_gst_token(driver):
    driver.get('https://gst-ai.accelya.io/gstportal/ui/ticket/TicketSearch.htm')
    time.sleep(1)
    WebDriverWait(driver,20)
    response = driver.page_source
    soup = BeautifulSoup(response, 'html.parser')
    select_element = soup.find('select', {'id': 'gst_number'})
    print("------------------",select_element)
    if select_element is not None:
        options = select_element.find_all('option')
        all_gst = [option['value'] for option in options]
    else:
        all_gst = []
    input_tag = soup.find('input', {'id': 'requestToken'})
    global requestToken
    requestToken = input_tag['value']

    global cookie
    cookies = driver.get_cookies()
    print("getting cookiessssssss",cookies)
    for eachcookie in cookies:
        if eachcookie['name'].startswith('JSESSIONID'):
            cookie = eachcookie['name']+'='+eachcookie['value']
            break
    return all_gst


def search_all_gst(all_gst,issue_date_form,issue_date_to):
    try:
        url = 'https://gst-ai.accelya.io/gstportal/ui/ticket/TicketSearch.htm'

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': cookie,
            'Origin': 'https://gst-ai.accelya.io',
            'Referer': 'https://gst-ai.accelya.io/gstportal/ui/ticket/TicketSearch.htm',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
        }

        data = {
            'requestToken': requestToken,
            'deleteRowNumHidden': '',
            'DeleteDetails': 'N',
            'referrer': '/ui/ticket/TicketSearch.htm',
            'detailPageMode': '02',
            'selectedRow': '',
            'searchLog': 'Y',
            'gst_number_value': ','.join(all_gst),
            'form_name': 'searchSection',
            'gst_number': all_gst,
            'ticket_number': '',
            'issue_date_form': issue_date_form,
            'issue_date_to': issue_date_to,
            'gstrDate': '',
            'Search': 'Search'
        }

        requests.post(url, headers=headers, data=data)

        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Cookie': cookie,
            'Origin': 'https://gst-ai.accelya.io',
            'Referer': 'https://gst-ai.accelya.io/gstportal/ui/ticket/TicketSearch.htm',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        }

        data = {
            'selectRowNumber': 'TicketDetailListSection',
            'changeSelectName': 'selectPageNumber',
            'tableData': '',
            'event': 'change',
            'undefined': '',
            'selectPageNumber_TicketDetailListSection': '100000',
            'requestToken': requestToken
        }

        
        print("passed cookiesss",cookie)
        print("urrrlll",url,"headerssssss",headers,"dddaaaattttaaa",data)

        response = requests.post(url, headers=headers, data=data)
        print("Response Content:", response.text)
        soup = BeautifulSoup(response.text, 'html.parser')
        print("Parsed Soup:", soup)
        
        time.sleep(15)
        table = soup.find('table')
        # Initialize an empty list to store the table data
        table_data = []

        # Find all rows in the table
        if table is not None:
            rows = table.find_all('tr')
        else:
            print("Table not found!")

        # Get the column names from the table header (first row)
        header_row = rows[0]
        column_names = [th.text.strip() for th in header_row.find_all('th')]

        # Iterate over the remaining rows
        for row in rows[1:]:
            # Get the data cells in the row
            cells = row.find_all('td')
            
            # Create a dictionary to store the row data
            row_data = {}
            
            # Iterate over the cells and map the data to column names
            for i in range(len(cells)):
                column_name = column_names[i]
                cell_text = cells[i].text.strip()
                row_data[column_name] = cell_text
            
            # Append the row data to the table data list
            table_data.append(row_data)

        # Find the biggest 'E-Ticket Issue Date'
        biggest_issue_date = max(table_data, key=lambda x: datetime.strptime(x['E-Ticket Issue Date'], '%d-%b-%Y'))

        # Remove rows with the biggest 'E-Ticket Issue Date'
        table_data = [row for row in table_data if row['E-Ticket Issue Date'] != biggest_issue_date['E-Ticket Issue Date']]

        return table_data, biggest_issue_date
    except Exception as e:
        retry = 0  # Define retry before using it
        if retry < 3:
            search_all_gst(all_gst,issue_date_form,issue_date_to,retry=retry+1)
            print("Exception happened: ",str(e))
        else:
            print("Exception happened: ", str(e))
            # logout(driver)
    

def logout(driver):
    try:
        print("Loging-Out")
        driver.find_element(By.CLASS_NAME,'loginUserName').click()
        WebDriverWait(driver,10).until(EC.visibility_of_element_located((By.LINK_TEXT, 'Logout')))
        driver.find_element(By.LINK_TEXT,'Logout').click()
    except Exception as e:
        print("Logout Error ", str(e))

temp_invoice_id = []
def get_invoices(gst,ticket,ticket_issue_date ):
    url = 'https://gst-ai.accelya.io/gstportal/ui/ticket/TicketSearch.htm?actionLink=view_invoice_number&value=v&airline_code=098&appType=REPORT&pnrNo=null&rowIndex=0&page=0&gst_number='+gst+'&ticket_number='+ticket+'&event=click&view_invoice_number_0=1&requestToken='+requestToken+''
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'Cookie': cookie,
        'Referer': 'https://gst-ai.accelya.io/gstportal/ui/ticket/TicketSearch.htm',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"'
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text.replace('<![CDATA[',''), 'html.parser')
    table = soup.find('table')
    # Initialize an empty list to store the table data
    table_data = []

    # Find all rows in the table
    rows = table.find_all('tr')

    # Get the column names from the table header (first row)
    header_row = rows[0]
    column_names = [th.text.strip() for th in header_row.find_all('th')]

    # Iterate over the remaining rows
    for row in rows[1:]:
        # Get the data cells in the row
        cells = row.find_all('td')
        
        # Create a dictionary to store the row data
        row_data = {}
        
        # Iterate over the cells and map the data to column names
        for i in range(len(cells)):
            column_name = column_names[i]
            cell_text = cells[i].text.strip()
            row_data[column_name] = cell_text
        
        # Append the row data to the table data list
        if not row_data['Invoice Number'] in temp_invoice_id:
            table_data.append(row_data)
            temp_invoice_id.append(row_data['Invoice Number'])

    def process_row(eachrow):
        url = 'https://gst-ai.accelya.io/gstportal/ui/ticket/TicketSearch.htm'
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Cookie': cookie,
            'Referer': 'https://gst-ai.accelya.io/gstportal/ui/ticket/TicketSearch.htm',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        }

        params = {
            'actionLink': 'invoice_number_Attach',
            'value': 'v',
            'rowIndex': '0',
            'page': '0',
            'appType': 'REPORT',
            'supportFileName': eachrow['invoice_no']
        }

        response = requests.get(url, headers=headers, params=params, verify=False)

        # Check if the request was successful
        if response.status_code == 200:         
            # Save the PDF file
            filename = eachrow['invoice_no'] + '.pdf'
            print("filename",filename)
            # Assuming filename is defined earlier in your code
            if response.status_code == 200:
                # Save the PDF file in the created directory
                filepath = os.path.join(directory_path, filename)
                with open(filepath, 'wb') as file:
                    file.write(response.content)
                    
                    # Upload the file to S3 (assuming the upload_s3 function works as expected)
                    status, s3_link = upload_s3(f'scrapers/{filepath}/{filename}', filename, 'airindia')
                    print("status,s3_link", status, s3_link)
                if status:
                    eachrow['s3_link'] = s3_link
                    try:
                        # Execute the INSERT query
                        with conn, conn.cursor() as cursor:
                            # Construct the INSERT query
                            insert_query = """
                                INSERT INTO airline_engine_scraper_airindia
                                (id, gstin_no, ticket_no, ticket_issue_date, invoice_no, invoice_issue_date, s3_link)
                                VALUES (%(id)s, %(gstin_no)s, %(ticket_no)s, %(ticket_issue_date)s, %(invoice_no)s, %(invoice_issue_date)s, %(s3_link)s);
                            """
                            # Execute the INSERT query with the sample data
                            cursor.execute(insert_query, eachdata)
                            # Commit the transaction
                            conn.commit()
                    except Exception as e:
                        print("Error inserting data into PostgreSQL:", e)
                    finally:
                        message={
                                "source":"LOGIN_SCRAPER",
                                "success": True,
                                "message": "FILES_PUSHED_TO_S3",
                                "guid":None,
                                "data": {'s3_link': [s3_link], 'airline':'airindia'}
                            }
                        sqs_client.send_message(
                            QueueUrl=AIRLINE_ENGINE_SCRAPER_OUTPUT_Q,
                            MessageBody=json.dumps(message)
                        )
                # os.remove(f'scrapers/temp/{filename}')
        else:
            print("Request failed with status code:", response.status_code)

    # Convert date strings to datetime objects
    filtered_data =[]
    for eachdata in table_data:
        id = hashlib.sha256((gst+ticket+eachdata['Invoice Number']).encode('utf-8')).hexdigest()
        formated_ticket_issue_date_obj = datetime.strptime(ticket_issue_date, "%d-%b-%Y")
        formated_invoice_issue_date_obj = datetime.strptime(eachdata['Invoice Issue Date'], "%d-%b-%Y")
        formated_ticket_issue_date = formated_ticket_issue_date_obj.strftime('%Y-%m-%d')
        formated_invoice_issue_date = formated_invoice_issue_date_obj.strftime('%Y-%m-%d')
        eachdata['id'] = str(id)
        eachdata['gstin_no'] = gst
        eachdata['ticket_no'] = ticket
        eachdata['ticket_issue_date'] = formated_ticket_issue_date
        eachdata['invoice_issue_date'] = formated_invoice_issue_date
        eachdata['invoice_no'] = eachdata['Invoice Number']
        filtered_data.append(eachdata)
   
    # Create a ThreadPoolExecutor with the desired number of threads
    num_threads = 1 
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Submit tasks to the executor for each row in the table
        futures = [executor.submit(process_row, row) for row in filtered_data]

        # Wait for all tasks to complete
        concurrent.futures.wait(futures)

        
def scrape_data(portal_email,portal_pass,from_date,to_date):
        driver = _web_driver()
        login(driver, portal_email, portal_pass)
        all_gst = get_gst_token(driver)
        print("all_gstall_gstall_gstall_gst",all_gst)
        issue_date_from = datetime.strptime(from_date, '%d-%b-%Y')
        issue_date_to = datetime.strptime(to_date, '%d-%b-%Y')

        print("datessssss",issue_date_from ,issue_date_to )

        while True:
            table_data, biggest_issue_date = search_all_gst(all_gst, issue_date_from.strftime('%d-%b-%Y'), issue_date_to.strftime('%d-%b-%Y'))
            biggest_issue_date_found = datetime.strptime(biggest_issue_date['E-Ticket Issue Date'], '%d-%b-%Y')
            for row in table_data:
                try:
                    get_invoices(row['GSTIN Number'],row['E-Ticket Number'],row['E-Ticket Issue Date'])
                except Exception as e:
                    continue
            if biggest_issue_date_found < issue_date_to:
                issue_date_from = biggest_issue_date_found
                with open("airindia_biggest_issue_date.txt", 'w') as txtfile:
                    txtfile.write(str(issue_date_from))
            else:
                break

        logout(driver)


def main():  # Modify the below changes here aswell portal_email = email , portal pass = password 

    portal_email = "Airlines_Ticket@mckinsey.com"
    portal_pass = "Tarun@7020"
    from_date = "01-Dec-2023"
    to_date = "14-Mar-2024"
    

    scrape_data(portal_email,portal_pass,from_date,to_date)

main()
