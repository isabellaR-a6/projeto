// Service worker: recebe os avisos de contas a pagar mesmo com o app fechado.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

self.addEventListener('push', (e) => {
  let aviso = {};
  try { aviso = e.data ? e.data.json() : {}; } catch { aviso = { titulo: e.data?.text() }; }
  e.waitUntil(self.registration.showNotification(aviso.titulo || 'Minhas Finanças', {
    body: aviso.corpo || '',
    icon: 'icon-192.png',
    badge: 'badge-96.png',
    tag: aviso.tag || 'avisos',
    renotify: true,
    data: { url: aviso.url || './' },
  }));
});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const destino = new URL(e.notification.data?.url || './', self.registration.scope).href;
  e.waitUntil((async () => {
    const abertas = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    const aberta = abertas.find((c) => c.url.startsWith(self.registration.scope));
    if (aberta) return aberta.focus();
    return self.clients.openWindow(destino);
  })());
});
