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
