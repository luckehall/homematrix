import axios from 'axios'

const api = axios.create({
  baseURL: 'https://homematrix.iotzator.com',
  withCredentials: true,  // necessario per il cookie refresh_token
})

// Interceptor: se access token scaduto, prova refresh automatico
api.interceptors.response.use(
  res => res,
  async err => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        const { data } = await axios.post(
          'https://homematrix.iotzator.com/api/auth/refresh',
          {}, { withCredentials: true }
        )
        localStorage.setItem('access_token', data.access_token)
        original.headers['Authorization'] = `Bearer ${data.access_token}`
        return api(original)
      } catch {
        localStorage.removeItem('access_token')
        window.location.href = '/'
      }
    }
    return Promise.reject(err)
  }
)

// Inietta access token ad ogni richiesta
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers['Authorization'] = `Bearer ${token}`
  return config
})

export default api
