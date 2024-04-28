from datetime import datetime
import os
import time
from flask import Flask, request, jsonify
import json
from datetime import datetime

from flask_cors import CORS
from airindia_fixed import scrape_data
from utils.pg import get_otp_reference, update_details

app = Flask(__name__)
CORS(app)

@app.route('/scrape', methods=['POST'])
def handle_scrape():
    
    print("Full request data received:", request.json)
    email = request.json.get('email')
    password = request.json.get('password')
    from_date = request.json.get('formattedFromDate')  # Assuming this comes in as 'DD-MMM-YYYY'
    to_date = request.json.get('formattedToDate')      # Assuming this comes in as 'DD-MMM-YYYY'
    id = request.json.get('runid')
    try:
        os.system("python C:/Users/annav/Desktop/AirIndiaPyCopy/scrapers/airindia_fixed.py " + str(id) +" "+ str(email) +" "+str(password) +" "+str(from_date)+" " + str(to_date))
        return jsonify({"status": "success", "message": "Data scraping initiated successfully."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/send_otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    otp = request.json.get('otpVerification')
    runid = request.json.get('runid')
    print('OTP:', otp, 'RunID:', runid)
    try:
        # Here, you would call update_details or a similar function to update the record
        update_details(runid, otp, 'OTP_RECIEVED')  # Assuming 'completed' is the status you set upon successful verification
        return jsonify({"status": "success", "message": "OTP verified. Continuing scraping."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

@app.route('/get_otp_ref/<id>', methods=['GET'])
def get_otp_ref(id):
    # Assuming `get_otp_reference` fetches the OTP reference from the database
    otp_ref = get_otp_reference(id)
    if otp_ref:
        return jsonify({'otp_ref': otp_ref}), 200
    else:
        return jsonify({'error': 'No OTP reference found'}), 404



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
