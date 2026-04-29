import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import App from './App';
import { ToastProvider } from './components/Toast';
import { TokenProvider } from './components/TokenContext';
import { MembershipProvider } from './components/MembershipContext';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <HelmetProvider>
      <BrowserRouter>
        <ToastProvider>
          <MembershipProvider>
            <TokenProvider>
              <App />
            </TokenProvider>
          </MembershipProvider>
        </ToastProvider>
      </BrowserRouter>
    </HelmetProvider>
  </React.StrictMode>
);
