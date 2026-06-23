importScripts('/static/web-push-config.js');

(function () {
  var config = self.__WEB_PUSH_CONFIG__ || {};
  var firebaseConfig = config.firebase || {};
  var requiredFields = ['apiKey', 'authDomain', 'projectId', 'messagingSenderId', 'appId'];
  var hasConfig = requiredFields.every(function (field) {
    return Boolean(firebaseConfig[field]);
  });

  if (!hasConfig) {
    self.addEventListener('push', function (event) {
      var payload = {};
      try {
        payload = event.data ? event.data.json() : {};
      } catch (error) {
        payload = {};
      }

      var title = payload.title || 'Seferim Nerede';
      var options = {
        body: payload.body || 'Yeni bir sefer bildirimi var.',
        data: payload.data || {}
      };

      event.waitUntil(self.registration.showNotification(title, options));
    });
    return;
  }

  importScripts('https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js');
  importScripts('https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js');

  firebase.initializeApp({
    apiKey: firebaseConfig.apiKey,
    authDomain: firebaseConfig.authDomain,
    projectId: firebaseConfig.projectId,
    storageBucket: firebaseConfig.storageBucket,
    messagingSenderId: firebaseConfig.messagingSenderId,
    appId: firebaseConfig.appId
  });

  var messaging = firebase.messaging();

  messaging.onBackgroundMessage(function (payload) {
    var notification = payload.notification || {};
    var title = notification.title || 'Seferim Nerede';
    var options = {
      body: notification.body || 'Yeni bir sefer bildirimi var.',
      data: payload.data || {}
    };

    self.registration.showNotification(title, options);
  });
})();

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  event.waitUntil(clients.openWindow('/'));
});
