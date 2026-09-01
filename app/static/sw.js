/* ResumeLens service worker — app-shell caching only.
   Upload/analysis, history and any POST request stay online-only. */

const CACHE_VERSION = "resumelens-v1";
const SHELL_CACHE = `${CACHE_VERSION}-shell`;

const SHELL_ASSETS = [
  "/",
  "/offline",
  "/static/css/main.css?v=2",
  "/static/js/main.js",
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) =>
      Promise.all(
        SHELL_ASSETS.map((url) =>
          cache.add(url).catch(() => null) // never fail install on one missing asset
        )
      )
    )
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key.startsWith("resumelens-") && key !== SHELL_CACHE)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Never intercept non-GET requests (uploads, analysis, delete, clear).
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Keep analysis / history / db-backed pages online-only — never cache or
  // serve them from the cache, so results are always current.
  const onlineOnlyPaths = ["/analyse", "/history"];
  if (onlineOnlyPaths.some((p) => url.pathname.startsWith(p))) {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match("/offline").then((r) => r || new Response("Offline", { status: 503 }))
      )
    );
    return;
  }

  // App-shell / static assets: cache-first, falling back to network.
  if (url.pathname.startsWith("/static/") || url.pathname === "/") {
    event.respondWith(
      caches.match(request).then((cached) => {
        const network = fetch(request)
          .then((response) => {
            if (response && response.ok) {
              caches.open(SHELL_CACHE).then((cache) => cache.put(request, response.clone()));
            }
            return response;
          })
          .catch(() => cached || caches.match("/offline"));
        return cached || network;
      })
    );
    return;
  }

  // Everything else: network-first, offline fallback for page navigations.
  event.respondWith(
    fetch(request).catch(() => {
      if (request.mode === "navigate") {
        return caches.match("/offline");
      }
      return caches.match(request);
    })
  );
});
