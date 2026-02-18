/* Minimal service worker: offline fallback */
const CACHE = "gfs-winter-v1";

self.addEventListener("install", (e) => {
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request).then((r) => r || caches.match("/").then((r2) => r2 || new Response("Offline. Try again when connected.", { status: 503, statusText: "Service Unavailable" })))
  );
});
