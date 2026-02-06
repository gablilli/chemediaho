/**
 * Runtime Configuration for che media ho?
 * 
 * This file provides global configuration for the frontend.
 * 
 * IMPORTANT: This is the ONLY place where the backend URL should be configured.
 * All API calls go through window.APP_CONFIG.API_BASE.
 * 
 * MODES:
 * 
 * 1. STANDALONE MODE (Docker all-in-one):
 *    API_BASE: "" (empty string = same origin)
 *    The Flask backend serves both the frontend and the API.
 * 
 * 2. VERCEL + LOCAL API MODE:
 *    API_BASE: "https://your-tunnel.ngrok.io" (your ngrok/Cloudflare Tunnel URL)
 *    API_KEY: "your-api-key" (for authentication)
 *    The frontend is deployed on Vercel, the API runs locally.
 */
window.APP_CONFIG = {
  // Empty string = same origin (standalone mode)
  // Set to your tunnel URL for Vercel deployment
  API_BASE: "",
  
  // API key for authentication (only needed for cross-origin mode)
  API_KEY: null
};

// Validate configuration on load
(function validateConfig() {
  if (typeof window.APP_CONFIG.API_BASE !== 'string') {
    console.error('[APP_CONFIG] API_BASE must be a string');
  }
  
  // Log configuration mode
  if (window.APP_CONFIG.API_BASE === '') {
    console.log('[APP_CONFIG] Running in STANDALONE mode (same origin)');
  } else {
    console.log('[APP_CONFIG] Running in CROSS-ORIGIN mode, API_BASE:', window.APP_CONFIG.API_BASE);
  }
})();
