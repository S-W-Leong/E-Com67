import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Amplify } from 'aws-amplify'
import App from './App.jsx'
import './index.css'

// AWS Amplify configuration using Vite environment variables
const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_USER_POOL_ID || 'placeholder',
      userPoolClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID || 'placeholder',
      region: import.meta.env.VITE_AWS_REGION || 'ap-southeast-1'
    }
  },
  API: {
    REST: {
      'e-com67-api': {
        endpoint: import.meta.env.VITE_API_ENDPOINT || 'https://placeholder.execute-api.ap-southeast-1.amazonaws.com/prod',
        region: import.meta.env.VITE_AWS_REGION || 'ap-southeast-1'
      }
    }
  }
}

Amplify.configure(amplifyConfig)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)