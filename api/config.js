export default function handler(req, res) {
  res.setHeader("Content-Type", "application/javascript");
  res.setHeader("Cache-Control", "no-store");

  res.end(`
    window.APP_CONFIG = {
      API_BASE: "${process.env.API_BASE ?? ''}",
      API_KEY: ${process.env.API_KEY ? `"${process.env.API_KEY}"` : 'null'}
    };

    (function validateConfig() {
      if (typeof window.APP_CONFIG.API_BASE !== 'string' || !window.APP_CONFIG.API_BASE) {
        console.error('[APP_CONFIG] API_BASE must be a non-empty string');
      }
    })();
  `);
}
