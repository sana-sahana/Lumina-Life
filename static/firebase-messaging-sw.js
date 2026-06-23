importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyBGMPyUU78tvaahRWapYNayHhhn5owDZ94",
  authDomain: "luminalife-7f217.firebaseapp.com",
  projectId: "luminalife-7f217",
  storageBucket: "luminalife-7f217.firebasestorage.app",
  messagingSenderId: "865095311959",
  appId: "1:865095311959:web:4efe29f8b1ea5699ebf912"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  self.registration.showNotification(
    payload.notification.title,
    {
      body: payload.notification.body,
      icon: "/i.png",
      badge: "/i.png"
    }
  );
});