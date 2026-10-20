/* Luises Identität: Offline-Modus. Speichert die App und lädt sie bei schlechter oder fehlender Verbindung aus dem Speicher. */
const CACHE = 'luise-offline-v1';
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(['./', './index.html']).catch(() => {})).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const r = e.request;
  if (r.method !== 'GET') return;
  const u = new URL(r.url);
  if (u.origin !== location.origin) return;
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const net = fetch(r).then(res => { if (res && res.ok) cache.put(r, res.clone()); return res; });
    net.catch(() => {});
    try {
      return await Promise.race([net, new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 3500))]);
    } catch (err) {
      const hit = (await cache.match(r, { ignoreSearch: true })) || (r.mode === 'navigate' ? (await cache.match('./index.html')) || (await cache.match('./')) : null);
      if (hit) return hit;
      try { return await net; } catch (e2) { return new Response('Offline', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } }); }
    }
  })());
});
