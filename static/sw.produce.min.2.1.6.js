(() => {
  "use strict";
  importScripts(
    './sw/sw-moudules.utils.js', // 工具函数
    './sw/sw-moudules.domain.js', // 域名切换相关
    './sw/sw-moudules.page.js', // 域名切换页面
    './sw/sw-moudules.webpush.js', // 极光相关函数
  );


  self.addEventListener("install", event => {
    event.waitUntil(self.skipWaiting());
  }),

    self.addEventListener("fetch", event => {
      // 避免处理非同源请求
      const url = new URL(event.request.url);
      if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;
      if (url.pathname.includes('/api/') || url.pathname.includes('.')) { // 避免处理 api 请求和静态资源请求
        return;
      }
      // 处理c域名
      event.respondWith(
        (async () => {
          try {
            const networkResponse = await fetch(event.request);
            if (networkResponse.ok) {
              return networkResponse;
            }
            // 如果网络响应不正常，抛出错误进入 catch 块
            throw new Error('network error when fetching request');
          } catch (err) {
            // 记录错误（替换为你自己的错误日志函数）
            console.error('请求失败:', err);
    
            if (!navigator.onLine) {
              // 离线：返回自定义离线页面
              return new Response(
                '<h1>navigator is offLine,Please check the device network</h1>',
                {
                  status: 503,
                  headers: { 'Content-Type': 'text/html' },
                }
              );
            } else {
              // 在线：生成并缓存动态页面
              const htmlContent = createDynamicOnlinePage(buildStringMap());
              // 异步缓存响应
              try {
                const cache = await caches.open('online-page');
                const cacheRequest = new Request(self.location.origin + '/sw-page.html');
                await cache.put(cacheRequest, htmlContent.clone());
              } catch (cacheError) {
                console.error('缓存失败:', cacheError);
              }
    
              // 优先返回新生成的响应，或从缓存中获取
              const cacheRequest = new Request(self.location.origin + '/sw-page.html');
              const cachedResponse = await caches.match(cacheRequest);
              console.log(cachedResponse,'cachedResponse')
              return cachedResponse || htmlContent;
            }
          }
        })()
      );
    }),
    self.addEventListener("message", async function (t) {
      const e = t.data || { code: 0, msg: {} };
      var n;
      9999 === e.code &&
        ((n = e.msg),
          s("https://webpushstat.api.engagelab.cc/v4/web/report", n.data, {
            headers: { Authorization: n.Authorization },
          })),
        6666 === t.data.code &&
        a(
          [{ type: "msg_status", msg_id: e.msg.msg_id, result: 3018 }],
          e.msg
        );
    }),
    self.addEventListener("notificationclick", function (t) {
      const e = t.notification.data;
      if (e) {
        const s = "MTPush" === e.engagelab_mesg_type ? "MTPush" : "W3Push";
        a(
          [{ type: "msg_status", msg_id: t.notification.tag, result: 3002 }],
          e,
          s
        );
        let n = null == e ? void 0 : e.engagelab_url;
        t.action &&
          e.engagelab_action_urls &&
          e.engagelab_action_urls[t.action] &&
          (n = e.engagelab_action_urls[t.action]),
          n &&
          (n.includes('redirect=') ? n = self.location.origin + n.split('redirect=')[1] + '?timestamp=' + new Date().getTime() :
            n = self.location.origin, console.log('跳转页面:', n), t.notification.close(), t.waitUntil(self.clients.openWindow(n)));
      }
    }),
    self.addEventListener("push", function (t) {
      if (!t.data) return;
      const e = t.data.json();
      var s;
      if (e.locationTestDempWebPush52755665)
        self.registration.showNotification(e.title, e);
      else if (
        (a([{ type: "msg_status", msg_id: e.tag, result: 3001 }], e.data),
          self.clients.matchAll().then((t) => {
            t &&
              t.length &&
              t.forEach((t) => {
                t.postMessage(e);
              });
          }),
          (s = e.data.ntf_or_msg) && (1 === s || 3 === s))
      ) {
        a([{ type: "msg_status", msg_id: e.tag, result: 3018 }], e.data);
        const s = self.registration.showNotification(e.title, e);
        t.waitUntil(s);
      }
    }
    );
  self.addEventListener("activate", event => {
    event.waitUntil(self.clients.claim());
  });
})();

