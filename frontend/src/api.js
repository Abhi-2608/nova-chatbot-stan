import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const chatAPI = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json"
  },
  timeout: 30000 // 30 second timeout
});

// Request Interceptor
chatAPI.interceptors.request.use(
  (config) => {
    // Add any authentication tokens if needed
    // const token = localStorage.getItem("authToken");
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    
    console.log("Request:", config.method.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error("Request error:", error);
    return Promise.reject(error);
  }
);

// Response Interceptor
chatAPI.interceptors.response.use(
  (response) => {
    console.log("Response:", response.status, response.data);
    return response;
  },
  (error) => {
    let errorMessage = "An error occurred";

    if (error.response) {
      // Server responded with error status
      const status = error.response.status;
      const data = error.response.data;

      switch (status) {
        case 400:
          errorMessage = data.message || "Bad request. Check your input.";
          break;
        case 401:
          errorMessage = "Unauthorized. Please log in.";
          break;
        case 403:
          errorMessage = "Forbidden. You don't have access.";
          break;
        case 404:
          errorMessage = "Server endpoint not found.";
          break;
        case 500:
          errorMessage = "Server error. Please try again later.";
          break;
        default:
          errorMessage = data.message || `Error: ${status}`;
      }
    } else if (error.request) {
      // Request made but no response
      errorMessage = "No response from server. Check your connection.";
    } else {
      // Error in request setup
      errorMessage = error.message || "Network error";
    }

    console.error("API Error:", errorMessage);
    return Promise.reject(new Error(errorMessage));
  }
);

export default chatAPI;