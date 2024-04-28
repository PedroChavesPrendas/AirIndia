import React, { useEffect, useState } from "react";
import { TextField, Button, Typography, Container, Paper } from "@mui/material";
import "./page1.css";
import { Link } from "react-router-dom";



const generateRandomOTP = () => {
  return Math.floor(100000 + Math.random() * 900000); // Generates a random 6-digit OTP
};

const formatDate = (dateString) => {
  const date = new Date(dateString);
  const formattedDate = date.toISOString().split("T")[0]; // Extracting yyyy-mm-dd from ISO format
  return formattedDate;
};

const Page1 = () => {
  const [from_date, setStartDate] = useState("");
  const [to_date, setEndDate] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState(""); // Added state for password
  const [expectedPDF, setExpectedPDF] = useState("");
  const [otpVerification, setOtpVerification] = useState("");
  const [randomOTP, setRandomOTP] = useState("");
  const [selectedPDFs, setSelectedPDFs] = useState([]);
  const [otpResult, setOtpResult] = useState("");
  const [otpRef, setOtpRef] = useState('');
  const [loading, setLoading] = useState(false);
  const [runId, setRunid] = useState('');

  

  const handleStartDateChange = (e) => {
    setStartDate(e.target.value);
  };

  const handleEndDateChange = (e) => {
    setEndDate(e.target.value);
  };

  const handleEmailChange = (e) => {
    setEmail(e.target.value);
  };

  const handlePasswordChange = (e) => {
    setPassword(e.target.value); // Handler function to update password state
  };

  const handleExpectedPDFChange = (e) => {
    setExpectedPDF(e.target.value);
  };

  const handleOtpVerificationChange = (e) => {
    setOtpVerification(e.target.value);
  };

  const formatDate = (dateString) => {
    if (!dateString) {
      console.error("Invalid date string:", dateString);
      return ""; // Return a default value or handle it appropriately
    }

    const dateParts = dateString.split("-"); // Split the dateString by "-"
    if (dateParts.length !== 3) {
      console.error("Date string does not match expected format:", dateString);
      return ""; // Handle format mismatch
    }

    const year = dateParts[0];
    const month = dateParts[1];
    const day = dateParts[2];

    // Map of month numbers to their short forms
    const monthMap = {
      "01": "Jan",
      "02": "Feb",
      "03": "Mar",
      "04": "Apr",
      "05": "May",
      "06": "Jun",
      "07": "Jul",
      "08": "Aug",
      "09": "Sep",
      10: "Oct",
      11: "Nov",
      12: "Dec",
    };

    // Format the date into the desired format "dd-MMM-yyyy"
    return `${day}-${monthMap[month]}-${year}`;
  };


  useEffect(() => {
    if (runId) {
      setLoading(true);
      const interval = setInterval(() => {
        fetch(`http://localhost:5000/get_otp_ref/${runId}`)
          .then(response => response.json())
          .then(data => {
            if (data.otp_ref) {
              setOtpRef(data.otp_ref);
              setLoading(false);
              clearInterval(interval);
            }
          })
          .catch(error => {
            console.error('Error fetching OTP reference:', error);
            setLoading(false);
          });
      }, 5000);  // Poll every 5 seconds

      return () => clearInterval(interval);
    }
  }, [runId]);

  const handleGenerateOTPClick = async () => {
    try {
      const formattedFromDate = formatDate(from_date);
      const formattedToDate = formatDate(to_date);
      const runid = Date.now()
      sessionStorage.setItem("runid", runid);
      setRunid(runid)
      const bodyContent = JSON.stringify({
        email,
        password,
        formattedFromDate,
        formattedToDate,
        runid,
      });
      console.log("Request payload:", bodyContent); // Log the request payload

      const response = await fetch("http://localhost:5000/scrape", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: bodyContent,
      });

      const data = await response.json();
      console.log("Response from server:", data);
    } catch (error) {
      console.error("Error during login:", error);
    }
  };

  const handleLogButtonClick = () => {
    const logData = {
      from_date: formatDate(from_date), // Format the date before saving to logData
      to_date: formatDate(to_date), // Format the date before saving to logData
      email,
      password, // Include password in log data
      expectedPDF,
      otpVerification,
      randomOTP,
    };
    setSelectedPDFs([...selectedPDFs, logData]);
  };

  const handleVerifyOTPClick = async () => {
    const runid = sessionStorage.getItem("runid"); // Retrieve the runid from sessionStorage

    try {
      const response = await fetch("http://localhost:5000/send_otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ otpVerification, runid }),
      });

      const data = await response.json();
      console.log(data);
    } catch (error) {
      console.error("Error during OTP verification:", error);
      setOtpResult("Failed to verify OTP due to an error.");
    }
  };

  

  

  const pollForOtpRef = (runId) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:5000/get_otp_ref/${runId}`);
        const data = await response.json();
        if (response.ok && data.otp_ref) {
          setOtpRef(data.otp_ref);
          clearInterval(interval); // Stop polling once the otp_ref is retrieved
          console.log("OTP Reference fetched:", data.otp_ref);
        } else {
          console.log("Still waiting for OTP reference...");
        }
      } catch (error) {
        console.error("Polling error:", error);
        clearInterval(interval); // Consider stopping polling on error or implement retry logic
      }
    }, 5000); // Poll every 5 seconds, adjust as needed based on expected delays
  };


  const handleSubmitButtonClick = () => {
    // Convert selectedPDFs to a table format
    const tableContent = selectedPDFs.map(
      (data, index) =>
        `<tr key=${index}><td>${data.startDate}</td><td>${data.endDate}</td><td>${data.email}</td><td>${data.password}</td><td>${data.expectedPDF}</td><td>${data.otpVerification}</td><td>${data.randomOTP}</td></tr>`
    );

    // Combine the table rows and add table tags
    const tableHTML = `<table><thead><tr><th>Start Date</th><th>End Date</th><th>Email</th><th>Password</th><th>Expected PDF</th><th>OTP Verification</th><th>Random OTP</th></tr></thead><tbody>${tableContent.join(
      ""
    )}</tbody></table>`;

    // Store the table HTML in local storage
    localStorage.setItem("selectedPDFsTable", tableHTML);
  };

  return (
    <div className="App">
      <Container
        component={Paper}
        maxWidth="100%"
        style={{
          padding: "20px",
          marginTop: "20px",
          background: "linear-gradient(to bottom,#BADAF5, white)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <img
            src="https://media.licdn.com/dms/image/C510BAQEJ9KUhl0TuxA/company-logo_200_200/0/1630629051409?e=2147483647&v=beta&t=QAb0CNhaDUoos0FdJUvhnUzVY8qdvhtZ8gkt442XYxk"
            alt="Logo"
            style={{ width: "50px", height: "50px" }}
          />
          {/* <label>
            <b>Finkraft</b>
          </label> */}
        </div>
        <br />
        <hr />
        <br />
        <div className="div1">
          <div style={{ display: "flex", alignItems: "center", gap: "120px" }}>
            <label>Start Date </label>
            <TextField
              type="date"
              value={from_date}
              onChange={handleStartDateChange}
              fullWidth
              margin="normal"
              InputLabelProps={{ shrink: true }}
              InputProps={{}} // Empty object to remove placeholder text
              sx={{ width: "30%" }}
              style={{
                width: "500px",
                height: "40px",
                background: "transparent",
              }}
            />
          </div>
          <br />
          <div style={{ display: "flex", alignItems: "center", gap: "125px" }}>
            <label>End Date</label>
            <TextField
              type="date"
              value={to_date}
              onChange={handleEndDateChange}
              fullWidth
              margin="normal"
              InputProps={{}} // Empty object to remove placeholder text
              sx={{ width: "30%" }}
              style={{
                width: "500px",
                height: "40px",
                background: "transparent",
              }}
            />
          </div>
          <br />
          <div style={{ display: "flex", alignItems: "center", gap: "150px" }}>
            <label>Email </label>
            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={handleEmailChange}
              fullWidth
              margin="normal"
              sx={{ width: "30%", marginBottom: "20px" }} // Adjust the width and margin as needed
              style={{
                width: "500px",
                height: "40px",
                background: "transparent",
              }}
            />
          </div>
          <br />
          {/* Password Field */}
          <div style={{ display: "flex", alignItems: "center", gap: "120px" }}>
            <label>Password </label>
            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={handlePasswordChange}
              fullWidth
              margin="normal"
              sx={{ width: "30%", marginBottom: "20px" }} // Adjust the width and margin as needed
              style={{
                width: "500px",
                height: "40px",
                background: "transparent",
              }}
            />
          </div>
          <br />
          <br />
          {/* Generate OTP Button and OTP Display */}
          <div style={{ display: "flex", alignItems: "center", gap: "55px" }}>
            <Button
              variant="contained"
              onClick={handleGenerateOTPClick}
              style={{ background: "transparent", color: "black" }}
            >
              Generate OTP
            </Button>
            {loading ? <Typography>Loading OTP Reference...</Typography> : <Typography>OTP Reference: {otpRef}</Typography>}
          </div>
          <br />
          <br />
          {/* Verify OTP Button and OTP Verification Text Field */}
          <div style={{ display: "flex", alignItems: "center", gap: "60px" }}>
            {/* <Button
              type="link"
              variant="contained"
              onClick={handleVerifyOTPClick}
              style={{
                width: "130px",
                background: "transparent",
                color: "black",
                border: "none",
              }}
            >
              Verify OTP
            </Button> */}
            <TextField
              label="OTP Verification"
              value={otpVerification}
              onChange={handleOtpVerificationChange}
              fullWidthmargin="normal"
              style={{
                width: "500px",
                height: "40px",
                background: "transparent",
              }}
            />
          </div>
          <br />
          <br />
          <br />
          {/* Submit and Log Buttons */}

          <div style={{ display: "flex", alignItems: "center", gap: "90px" }}>
            <Button
              variant="contained"
              onClick={handleVerifyOTPClick}
              style={{ width: "300px", height: "40px", background: "#4c8d9c" }}
            >
              Submit
            </Button>
            <Link to="Page2">
              <Button
                variant="contained"
                onClick={handleSubmitButtonClick}
                style={{
                  width: "300px",
                  height: "40px",
                  background: "#4c8d9c",
                }}
              >
                Log
              </Button>
            </Link>
          </div>
        </div>
        {/* Display Selected PDFs */}
        {selectedPDFs.map((data, index) => (
          <ul key={index}>
            <li>
              <strong>Start Date:</strong> {data.startDate}
            </li>
            <li>
              <strong>End Date:</strong> {data.endDate}
            </li>
            <li>
              <strong>Email:</strong> {data.email}
            </li>
            <li>
              <strong>Password:</strong> {data.password}
            </li>{" "}
            {/* Display password */}
            <li>
              <strong>Expected PDF:</strong> {data.expectedPDF}
            </li>
            <li>
              <strong>OTP Verification:</strong> {data.otpVerification}
            </li>
            <li>
              <strong>Random OTP:</strong> {data.randomOTP}
            </li>
          </ul>
        ))}
      </Container>
    </div>
  );
};

export default Page1;
