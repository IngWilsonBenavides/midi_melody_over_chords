import axios from "axios";

const client = axios.create({
  // All requests go through /api (proxied by Vite to the Django backend)
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

export default client;
