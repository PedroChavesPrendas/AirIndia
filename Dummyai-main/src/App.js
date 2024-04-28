import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'; // Import BrowserRouter, Routes, and Route
import Page1 from './page1/page1';
import Page2 from './page2/Page2'; // Assuming your component name is Page2

const App = () => {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<Page1 />} /> {/* Use 'element' prop for specifying component */}
          <Route path="/Page2" element={<Page2 />} /> {/* Use 'element' prop for specifying component */}
        </Routes>
      </div>
    </Router>
  );
};

export default App;
