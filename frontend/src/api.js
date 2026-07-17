import axios from "axios";

// Backend URL comes from an env var. Locally it falls back to your dev port.
// On Render you'll set VITE_API_URL to your deployed backend URL — no code change.
const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8010";

const api = axios.create({ baseURL: BASE_URL });

// Attach the JWT to every request automatically if we have one.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;