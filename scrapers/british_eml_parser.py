
import re

def extract_info_from_eml(eml_file_path):
    try:
        with open(eml_file_path, 'r') as file:
            eml_content = file.read()

        top_details = {}
        table_details = {}

        # Extracting top details
        top_details['Address'] = re.search(r'Address:\s*([\w\s,]+)', eml_content).group(1)
        top_details['GSTIN'] = re.search(r'GSTIN:\s*([\w\d]+)', eml_content).group(1)
        top_details['Passenger Name'] = re.search(r'Passenger Name:\s*([\w\s/]+)', eml_content).group(1)
        top_details['HSN'] = re.search(r'HSN:\s*(\d+)', eml_content).group(1)
        top_details['Tax Invoice #'] = re.search(r'Tax Invoice #:\s*(\S+)', eml_content).group(1)
        top_details['Bill To'] = re.search(r'Bill To:\s*([\w\s.]+)', eml_content).group(1)
        top_details['Email'] = re.search(r'Email:\s*([\w.@]+)', eml_content).group(1)
        top_details['Invoice Date'] = re.search(r'Invoice Date:\s*(\d+/\w+/\d+)', eml_content).group(1)
        top_details['Address (2)'] = re.search(r'Address:\s*([\w\s\d]+)', eml_content).group(1)
        top_details['POS'] = re.search(r'POS\s*(\d+-\w+)', eml_content).group(1)
        top_details['Ticket No'] = re.search(r'Ticket No\.\s*(\d+-\d+)', eml_content).group(1)
        top_details['GSTIN (2)'] = re.search(r'GSTIN:\s*(\d+\w+)', eml_content).group(1)
        top_details['PNR'] = re.search(r'PNR:\s*(\w+)', eml_content).group(1)

        # Extracting table details
        matches = re.findall(r'\d+\s+([\w\s]+)\s+([\d,.]+)', eml_content)
        for match in matches:
            table_details[match[0]] = match[1]

        return {'top_details': top_details, 'table_details': table_details}
    
    except Exception as e:
        print("Error:", e)

# Example usage
eml_file_path = "/Users/finkraft/dev/AirIndia_scrapers/scrapers/british.eml"
extracted_info = extract_info_from_eml(eml_file_path)
if extracted_info:
    print(extracted_info)
