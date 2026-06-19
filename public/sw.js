// Sambhav Vani Reel Studio — Service Worker
// Precaches the app shell; all API calls go to network.

const CACHE_NAME = 'svrs-v1';
const SHELL = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  // Google Fonts cached at runtime (see below)
];

// ── Install: cache shell ──────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL))
  );
  self.skipWaiting();
});

// ── Activate: delete old caches ──────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// ── Fetch strategy ───────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Never intercept API calls (Sarvam, Gemini, Groq, render service)
  const apiHosts = ['googleapis.com', 'generativelanguage.googleapis.com',
                    'api.groq.com', 'sarvam.ai', 'workers.dev',
                    'fly.dev', 'run.app', 'railway.app'];
  if (apiHosts.some(h => url.hostname.includes(h))) {
    return; // pass through
  }

  // Google Fonts — cache-first
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {
    event.respondWith(
      caches.open('svrs-fonts').then(cache =>
        cache.match(request).then(cached =>
          cached || fetch(request).then(resp => { cache.put(request, resp.clone()); return resp; })
        )
      )
    );
    return;
  }

  // App shell — cache-first, network fallback
  event.respondWith(
    caches.match(request).then(cached => cached || fetch(request).catch(() => caches.match('/index.html')))
  );
});
