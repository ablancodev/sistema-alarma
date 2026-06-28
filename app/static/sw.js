// Service worker mínimo: permite instalar la PWA. No cacheamos la lógica de red
// (las subidas siempre van a la red en vivo).
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function () { /* passthrough */ });
