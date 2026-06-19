/**
 * Sambhav Vani — Sarvam STT Proxy (Cloudflare Worker)
 *
 * Deploy:
 *   1. Install Wrangler:  npm install -g wrangler
 *   2. Login:             wrangler login
 *   3. Deploy:            wrangler deploy sarvam-proxy.js --name sarvam-proxy
 *
 * Your PWA's Sarvam Proxy URL will be:
 *   https://sarvam-proxy.<your-subdomain>.workers.dev
 *
 * The worker forwards:  POST /speech-to-text  →  Sarvam API
 * It passes the api-subscription-key header from the browser unchanged.
 * It NEVER stores the key — the browser sends it per-request.
 */

const SARVAM_BASE = "https://api.sarvam.ai";

// Allow requests from these origins only (add your Netlify/Vercel URL)
const ALLOWED_ORIGINS = [
  "https://your-pwa.netlify.app",       // ← replace
  "https://your-pwa.vercel.app",        // ← replace
  "http://localhost:3000",
  "http://localhost:5173",
  "http://127.0.0.1:5500",
];

function corsHeaders(origin) {
  const allowed = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allowed,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, api-subscription-key",
    "Access-Control-Max-Age": "86400",
  };
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const cors   = corsHeaders(origin);

    // Preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405, headers: cors });
    }

    const url     = new URL(request.url);
    const apiPath = url.pathname;                   // e.g. /speech-to-text
    const target  = SARVAM_BASE + apiPath + url.search;

    // Forward the original body unchanged (multipart/form-data)
    const proxyReq = new Request(target, {
      method:  "POST",
      headers: {
        "api-subscription-key": request.headers.get("api-subscription-key") || "",
      },
      body:    request.body,
      // duplex needed for streaming body forwarding
      ...(typeof request.duplex !== "undefined" ? { duplex: "half" } : {}),
    });

    try {
      const resp = await fetch(proxyReq);
      const body = await resp.arrayBuffer();
      return new Response(body, {
        status:  resp.status,
        headers: {
          ...cors,
          "Content-Type": resp.headers.get("Content-Type") || "application/json",
        },
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), {
        status:  502,
        headers: { ...cors, "Content-Type": "application/json" },
      });
    }
  },
};
