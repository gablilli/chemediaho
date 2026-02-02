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
export default function handler(req, res) {
  res.setHeader('Content-Type', 'application/javascript');
  res.setHeader('Cache-Control', 'no-store');

  const apiBase = process.env.BACKEND_BASE_URL || '';
  const apiKey = process.env.API_KEY || '';

  res.send(`
    window.APP_CONFIG = {
      API_BASE: ${JSON.stringify(apiBase)},
      API_KEY: ${JSON.stringify(apiKey)}
    };
  `);
}
