import { initializeApp } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-app.js";
import { getAuth, GoogleAuthProvider } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-auth.js";
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyB77lF1efUjrR3CzBffp9p5x98M6phYMQ8",
  authDomain: "flask-demo-59926.firebaseapp.com",
  projectId: "flask-demo-59926",
  storageBucket: "flask-demo-59926.firebasestorage.app",
  messagingSenderId: "879322438437",
  appId: "1:879322438437:web:1c729a03908c6b6595d8cc",
  measurementId: "G-GVJB1YWKY0"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();
export { auth, provider };