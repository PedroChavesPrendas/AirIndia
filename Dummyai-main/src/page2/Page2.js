import React from 'react'
import { TextField, Button, Typography, Container, Paper } from '@mui/material';
import './Page2.css';

const Page2 = () => {
  return (
    
    <div className="App">
      <Container maxWidth="100%" style={{ padding: '20px', marginTop: '20px',  background: 'linear-gradient(to bottom,#BADAF5, white)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      <img src="https://media.licdn.com/dms/image/C510BAQEJ9KUhl0TuxA/company-logo_200_200/0/1630629051409?e=2147483647&v=beta&t=QAb0CNhaDUoos0FdJUvhnUzVY8qdvhtZ8gkt442XYxk" alt="Logo" style={{ width: '50px', height: '50px' }} />
      {/* <label><b>Finkraft</b></label> */}
      </div><br/>
        <hr/><br/><br/><br/><br/>
        <div>
        <table>
        <tr class="center-heading">
        <th >End date</th>
        <th>Startdate</th>
        <th>Email</th>
        <th>SelectedPDFs</th>
        
        </tr>
        </table>
        </div>
      </Container>
    </div>
  )
}

export default Page2
