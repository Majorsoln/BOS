import axios from "axios";
import { API_BASE_URL } from "@/lib/constants";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// Request interceptor: inject API key + business context from localStorage
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const apiKey = localStorage.getItem("bos_api_key");
    const businessId = localStorage.getItem("bos_business_id");
    const branchId = localStorage.getItem("bos_branch_id");

    if (apiKey) {
      config.headers["Authorization"] = `Bearer ${apiKey}`;
    }

    // For POST requests, inject business_id + actor into body
    if (config.method === "post" && config.data && businessId) {
      const data = typeof config.data === "string" ? JSON.parse(config.data) : config.data;
      if (!data.business_id) data.business_id = businessId;
      if (branchId && !data.branch_id) data.branch_id = branchId;
      if (!data.actor_id) {
        data.actor_id = localStorage.getItem("bos_actor_id") || "";
      }
      config.data = data;
    }

    // For GET requests, inject business_id as query param if needed
    if (config.method === "get" && businessId) {
      config.params = config.params || {};
      if (!config.params.business_id) {
        config.params.business_id = businessId;
      }
    }
  }
  return config;
});

// Response interceptor: handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("bos_api_key");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

export default api;
