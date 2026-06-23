(function (root) {
  var existing = root.__WEB_PUSH_CONFIG__ || {};
  var firebase = existing.firebase || {};

  root.__WEB_PUSH_CONFIG__ = Object.assign({}, existing, {
    firebase: Object.assign(
      {
        apiKey: '',
        authDomain: '',
        projectId: '',
        storageBucket: '',
        messagingSenderId: '',
        appId: '',
        vapidKey: ''
      },
      firebase
    )
  });
})(typeof self !== 'undefined' ? self : window);
