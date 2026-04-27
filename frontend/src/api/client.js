import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// 요청 인터셉터
apiClient.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
);

// 응답 인터셉터
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export default apiClient;

// ── API 함수 모음 ──────────────────────────────────────────────

/** 온보딩 프로필 저장 */
export const saveProfile = (profileData) =>
  apiClient.post('/api/users/profile/', profileData);

/** 채팅 메시지 전송 */
export const sendMessage = (messageData) =>
  apiClient.post('/api/chat/', messageData);

/** 채팅 히스토리 조회 */
export const getChatHistory = (userId) =>
  apiClient.get(`/api/chat/history/${userId}/`);

/** 카드 목록 조회 */
export const getCards = () =>
  apiClient.get('/api/cards/');
