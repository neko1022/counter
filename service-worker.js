// ===== スロットカウンター Service Worker =====
// オフラインキャッシュ対応

const CACHE_NAME = 'slot-counter-v1';

// キャッシュするファイル一覧
const CACHE_FILES = [
  './',
  './index.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

// インストール時: キャッシュにファイルを保存
self.addEventListener('install', (event) => {
  console.log('[SW] インストール開始');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] キャッシュにファイルを追加');
        // 個別にキャッシュして、一つ失敗しても継続する
        return Promise.allSettled(
          CACHE_FILES.map(file =>
            cache.add(file).catch(err => console.warn('[SW] キャッシュ失敗:', file, err))
          )
        );
      })
      .then(() => {
        console.log('[SW] インストール完了');
        return self.skipWaiting();
      })
  );
});

// アクティベート時: 古いキャッシュを削除
self.addEventListener('activate', (event) => {
  console.log('[SW] アクティベート');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter(name => name !== CACHE_NAME)
          .map(name => {
            console.log('[SW] 古いキャッシュを削除:', name);
            return caches.delete(name);
          })
      );
    }).then(() => self.clients.claim())
  );
});

// フェッチ時: キャッシュファーストで応答
self.addEventListener('fetch', (event) => {
  // YouTubeのリクエストはキャッシュしない
  if (event.request.url.includes('youtube.com') ||
      event.request.url.includes('youtu.be') ||
      event.request.url.includes('ytimg.com')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then((cachedResponse) => {
        // キャッシュがあればそれを返す
        if (cachedResponse) {
          return cachedResponse;
        }
        // キャッシュがなければネットワークから取得
        return fetch(event.request)
          .then((response) => {
            // 有効なレスポンスのみキャッシュに追加
            if (response && response.status === 200 && response.type === 'basic') {
              const responseClone = response.clone();
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(event.request, responseClone);
              });
            }
            return response;
          })
          .catch(() => {
            // オフライン時のフォールバック
            if (event.request.destination === 'document') {
              return caches.match('./index.html');
            }
          });
      })
  );
});
