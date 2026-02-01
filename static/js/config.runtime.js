/**
 * Runtime Configuration for che media ho?
 * 
 * This file provides global configuration for the frontend.
 * When deployed to Vercel, environment variables will be injected at build time.
 * 
 * For local development, set these values directly or use environment variables:
 * - BACKEND_BASE_URL: The URL of the Flask backend (e.g., http://localhost:8001)
 * - API_KEY: The API key for authenticating with the backend (optional for local dev)
 * 
 * NOTE: In production on Vercel, these will be replaced with actual env vars at build time.
 * For local development without Vercel, you can modify this file directly.
 */
window.APP_CONFIG = {
  // Backend base URL - change this for local development
  // In Vercel, this will be: process.env.BACKEND_BASE_URL
  API_BASE: '',  // Empty string means same-origin (for local dev with backend on same host)
  
  // API key for backend authentication
  // In Vercel, this will be: process.env.API_KEY || null
  API_KEY: null
};

// Validate configuration on load
(function validateConfig() {
  // API_BASE can be empty (same-origin) or a valid URL
  // No validation error for empty API_BASE - this is valid for same-origin requests
  if (window.APP_CONFIG.API_BASE && typeof window.APP_CONFIG.API_BASE !== 'string') {
    console.error('[APP_CONFIG] API_BASE must be a string');
  }
})();
