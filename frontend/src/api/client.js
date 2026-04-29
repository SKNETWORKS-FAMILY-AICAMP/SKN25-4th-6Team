import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
});

apiClient.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export default apiClient;

export const sendMessage = (data) =>
  apiClient.post('/api/chat/', data);

export const getCards = () =>
  apiClient.get('/api/cards/');

export const getSessions = () =>
  apiClient.get('/api/sessions/');

export const createSession = (title) =>
  apiClient.post('/api/sessions/', { title });

export const getSessionDetail = (sessionId) =>
  apiClient.get(`/api/sessions/${sessionId}/`);

export const addMessage = (sessionId, role, text, payload = {}) =>
  apiClient.post(`/api/sessions/${sessionId}/`, { role, text, payload });

export const deleteSession = (sessionId) =>
  apiClient.delete(`/api/sessions/${sessionId}/`);
