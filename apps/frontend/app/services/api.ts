import axios from 'axios';

// Tạo đường dây nóng gọi thẳng tới Backend FastAPI
const api = axios.create({
  baseURL: 'http://localhost:8000', 
  headers: {
    'Content-Type': 'application/json',
  },
});

// Tự động nhét vé (Token) vào mọi request nếu sinh viên đã đăng nhập
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export default api;
