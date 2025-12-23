import axios from 'axios'

class ApiClient {
  constructor(baseURL, getAuthToken) {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json'
      }
    })
    
    this.getAuthToken = getAuthToken
    
    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      async (config) => {
        if (this.getAuthToken) {
          const token = await this.getAuthToken()
          if (token) {
            config.headers.Authorization = `Bearer ${token}`
          }
        }
        return config
      },
      (error) => Promise.reject(error)
    )
    
    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized access
          console.warn('Unauthorized access - token may be expired')
        }
        return Promise.reject(error)
      }
    )
  }
  
  async get(url, config = {}) {
    const response = await this.client.get(url, config)
    return response.data
  }
  
  async post(url, data = {}, config = {}) {
    const response = await this.client.post(url, data, config)
    return response.data
  }
  
  async put(url, data = {}, config = {}) {
    const response = await this.client.put(url, data, config)
    return response.data
  }
  
  async delete(url, config = {}) {
    const response = await this.client.delete(url, config)
    return response.data
  }
}

export default ApiClient