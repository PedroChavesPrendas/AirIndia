import csv
import os
import requests

# Function to download files from URLs in a CSV file
def download_files_from_csv(csv_file, url_column_name, save_dir):
    # Create directory if it doesn't exist
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    with open(csv_file, 'r', newline='') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            url = row[url_column_name]
            file_name = url.split("/")[-1]
            file_path = os.path.join(save_dir, file_name)

            # Send a GET request to the URL
            response = requests.get(url)
            
            # Check if the request was successful (status code 200)
            if response.status_code == 200:
                # Save the content of the response to a file
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                print(f"Downloaded {file_name}")
            else:
                print(f"Failed to download {file_name}. Status code: {response.status_code}")

# Example usage
csv_file = '/Users/finkraft/dev/AirIndia_scrapers/scrapers/Abbott_13th_Mar.csv'  # Path to your CSV file
url_column_name = 'S3_URL'  # Name of the column containing URLs
save_dir = './downloaded_files'  # Directory to save the downloaded files

download_files_from_csv(csv_file, url_column_name, save_dir)
