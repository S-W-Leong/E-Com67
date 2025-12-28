class ApiClient {
  constructor(baseURL, getAuthToken, httpClient = null) {
    // Allow axios to be injected, or use a default fetch-based implementation
    if (httpClient) {
      this.client = httpClient.create({
        baseURL,
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      // Request interceptor to add auth token
      this.client.interceptors.request.use(
        async (config) => {
          if (getAuthToken) {
            const token = await getAuthToken()
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
    } else {
      // Fallback to fetch-based implementation
      this.baseURL = baseURL
      this.getAuthToken = getAuthToken
    }
  }
  
  async _makeRequest(method, url, data = null, config = {}) {
    if (this.client) {
      // Use axios client
      const response = await this.client[method](url, data, config)
      return response.data
    } else {
      // Use fetch fallback
      const headers = {
        'Content-Type': 'application/json',
        ...config.headers
      }
      
      if (this.getAuthToken) {
        const token = await this.getAuthToken()
        if (token) {
          headers.Authorization = `Bearer ${token}`
        }
      }
      
      const fetchConfig = {
        method: method.toUpperCase(),
        headers,
        ...config
      }
      
      if (data && (method === 'post' || method === 'put')) {
        fetchConfig.body = JSON.stringify(data)
      }
      
      const response = await fetch(`${this.baseURL}${url}`, fetchConfig)
      
      if (response.status === 401) {
        console.warn('Unauthorized access - token may be expired')
      }
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      return await response.json()
    }
  }
  
  async get(url, config = {}) {
    return this._makeRequest('get', url, null, config)
  }
  
  async post(url, data = {}, config = {}) {
    return this._makeRequest('post', url, data, config)
  }
  
  async put(url, data = {}, config = {}) {
    return this._makeRequest('put', url, data, config)
  }
  
  async delete(url, config = {}) {
    return this._makeRequest('delete', url, null, config)
  }
}

export default ApiClient