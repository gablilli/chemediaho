/**
 * Runtime Configuration for che media ho?
 * 
 * This file provides global configuration for the frontend.
 * When deployed to Vercel, environment variables will be injected at build time.
 * 
 * IMPORTANT: This is the ONLY place where the backend URL should be configured.
 * All API calls go through window.APP_CONFIG.API_BASE.
 * 
 * For Vercel deployment, replace the values below with:
 * - API_BASE: Your ngrok/Cloudflare Tunnel URL to the local backend
 * - API_KEY: Your API key for backend authentication
 */
window.APP_CONFIG = {
  API_BASE: "https://api.gabrx.eu.org",
  API_KEY: none

// Validate configuration on load
(function validateConfig() {
  if (typeof window.APP_CONFIG.API_BASE !== 'string') {
    console.error('[APP_CONFIG] API_BASE must be a string');
  }
})();
