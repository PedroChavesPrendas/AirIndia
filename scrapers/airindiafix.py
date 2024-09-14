import requests
from bs4 import BeautifulSoup

import requests
from bs4 import BeautifulSoup
import requests

cookies = {
    'JSESSIONID': '5B16C6491AE7365F317CE80ECCDD57EA',
}

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-GB,en;q=0.9',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded',
    # 'Cookie': 'JSESSIONID=5B16C6491AE7365F317CE80ECCDD57EA',
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
    # Follow the steps on this document to remove sensitive information below: 
    # https://docs.github.com/en/enterprise-cloud@latest/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository 
    # Contact me in case you have any questions
    'requestToken': 'NBeG6tfspf9LxdTJQ4Wu',
    'deleteRowNumHidden': '',
    'DeleteDetails': 'N',
    'referrer': '/ui/ticket/TicketSearch.htm',
    'detailPageMode': '02',
    'selectedRow': '',
    'searchLog': 'Y',
    'gst_number_value': '06AAXFM1434F1Z7,29AAXFM1434F1ZZ,07AAXFM1434F1Z5,29AAACM8361R1ZN,27AAXFM1434F1Z3,33AAXFM1434F1ZA,33AAACM8361R1ZY,27AAACM8361R1ZR,06AAACM8361R1ZV',
    'form_name': 'searchSection',
    'gst_number': [
        '06AAXFM1434F1Z7',
        '29AAXFM1434F1ZZ',
        '07AAXFM1434F1Z5',
        '29AAACM8361R1ZN',
        '27AAXFM1434F1Z3',
        '33AAXFM1434F1ZA',
        '33AAACM8361R1ZY',
        '27AAACM8361R1ZR',
        '06AAACM8361R1ZV',
    ],
    'ticket_number': '',
    'issue_date_form': '01-Dec-2023',
    'issue_date_to': '29-Mar-2024',
    'gstrDate': '',
    'Search': 'Search',
}

response = requests.post(
    'https://gst-ai.accelya.io/gstportal/ui/ticket/TicketSearch.htm',
    cookies=cookies,
    headers=headers,
    data=data,
)

# Check if the response status code is 200 (OK)
if response.status_code == 200:
    print("API call successful")
    # Parse the response using BeautifulSoup
    soup = BeautifulSoup(response.text.replace('<![CDATA[',''), 'html.parser')
    print("Parsed response:")
    # print(soup)

    # Find the table in the parsed response
    table = soup.find('table')


    # Check if the table is found
    if table is not None:
        print("Table found")
        # Find all rows in the table
        rows = table.find_all('tr')

        # Initialize an empty list to store the table data
        table_data = []

        # Process the rows if any are found
        if rows:
            print("Rows found in the table")
            # Process the rows here
            # For example, you can loop through the rows and extract data
            for row in rows:
                # Assuming you want to print the content of each row
                print(row.text.strip())
        else:
            print("No rows found in the table")
    else:
        print("Table not found in the response")
else:
    print("Error: API call failed with status code", response.status_code)
