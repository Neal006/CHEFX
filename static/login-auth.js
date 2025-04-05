import { auth, provider } from "./firebase-config.js";
import { 
  signInWithEmailAndPassword,
  signInWithPopup,
  createUserWithEmailAndPassword,
  sendPasswordResetEmail,
  GoogleAuthProvider 
} from "https://www.gstatic.com/firebasejs/10.9.0/firebase-auth.js";

// Cache DOM elements
const elements = {
  signInWithGoogleBtn: document.getElementById("sign-in-with-google-btn"),
  signUpWithGoogleBtn: document.getElementById("sign-up-with-google-btn"),
  emailInput: document.getElementById("email-input"),
  passwordInput: document.getElementById("password-input"),
  signInBtn: document.getElementById("sign-in-btn"),
  createAccountBtn: document.getElementById("create-account-btn"),
  emailForgotPasswordEl: document.getElementById("email-forgot-password"),
  forgotPasswordBtn: document.getElementById("forgot-password-btn"),
  errorMsgEmail: document.getElementById("email-error-message"),
  errorMsgPassword: document.getElementById("password-error-message"),
  errorMsgGoogleSignIn: document.getElementById("google-signin-error-message")
};

// Initialize event listeners
function initEventListeners() {
  if (elements.signInWithGoogleBtn) {
    elements.signInWithGoogleBtn.addEventListener("click", handleGoogleSignIn);
  }

  if (elements.signInBtn) {
    elements.signInBtn.addEventListener("click", handleEmailSignIn);
  }

  if (elements.createAccountBtn) {
    elements.createAccountBtn.addEventListener("click", handleEmailSignUp);
  }

  if (elements.signUpWithGoogleBtn) {
    elements.signUpWithGoogleBtn.addEventListener("click", handleGoogleSignIn);
  }

  if (elements.forgotPasswordBtn) {
    elements.forgotPasswordBtn.addEventListener("click", handlePasswordReset);
  }
}

// Clear error messages
function clearErrors() {
  if (elements.errorMsgEmail) elements.errorMsgEmail.textContent = '';
  if (elements.errorMsgPassword) elements.errorMsgPassword.textContent = '';
  if (elements.errorMsgGoogleSignIn) elements.errorMsgGoogleSignIn.textContent = '';
}

// Set button state during authentication
function setButtonState(button, isLoading) {
  if (!button) return;
  
  button.disabled = isLoading;
  button.textContent = isLoading ? 'Please wait...' : button.dataset.originalText || button.textContent;
  
  if (!isLoading && !button.dataset.originalText) {
    button.dataset.originalText = button.textContent;
  }
}

// Handle Google Sign In
async function handleGoogleSignIn(e) {
  e.preventDefault();
  
  // Get the button that was clicked
  const button = e.currentTarget;
  
  try {
    clearErrors();
    setButtonState(button, true);
    
    // Configure Google provider
    provider.setCustomParameters({
      prompt: 'select_account'
    });
    
    const result = await signInWithPopup(auth, provider);
    const user = result.user;
    const idToken = await user.getIdToken(true);
    await loginUser(user, idToken);
  } catch (error) {
    console.error("Google sign-in error:", error);
    if (elements.errorMsgGoogleSignIn) {
      elements.errorMsgGoogleSignIn.textContent = "Failed to sign in with Google. Please try again.";
    }
    setButtonState(button, false);
  }
}

// Handle Email Sign In
async function handleEmailSignIn(e) {
  e.preventDefault();
  
  const email = elements.emailInput?.value;
  const password = elements.passwordInput?.value;

  if (!email || !password) {
    if (elements.errorMsgEmail) elements.errorMsgEmail.textContent = "Please enter both email and password";
    return;
  }

  try {
    clearErrors();
    setButtonState(elements.signInBtn, true);

    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    const user = userCredential.user;
    const idToken = await user.getIdToken(true);
    await loginUser(user, idToken);
  } catch (error) {
    handleAuthError(error);
    setButtonState(elements.signInBtn, false);
  }
}

// Handle Email Sign Up
async function handleEmailSignUp(e) {
  e.preventDefault();
  
  const email = elements.emailInput?.value;
  const password = elements.passwordInput?.value;

  if (!email || !password) {
    if (elements.errorMsgEmail) elements.errorMsgEmail.textContent = "Please enter both email and password";
    return;
  }

  if (password.length < 6) {
    if (elements.errorMsgPassword) elements.errorMsgPassword.textContent = "Password must be at least 6 characters";
    return;
  }

  try {
    clearErrors();
    setButtonState(elements.createAccountBtn, true);

    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    const user = userCredential.user;
    const idToken = await user.getIdToken(true);
    await loginUser(user, idToken);
  } catch (error) {
    handleAuthError(error);
    setButtonState(elements.createAccountBtn, false);
  }
}

// Handle Password Reset
async function handlePasswordReset(e) {
  e.preventDefault();
  
  const email = elements.emailForgotPasswordEl?.value;

  if (!email) {
    if (elements.errorMsgEmail) elements.errorMsgEmail.textContent = "Please enter your email address";
    return;
  }

  try {
    clearErrors();
    setButtonState(elements.forgotPasswordBtn, true);

    await sendPasswordResetEmail(auth, email);
    
    // Show success message
    const resetConfirmation = document.getElementById('reset-password-confirmation-page');
    const resetForm = document.getElementById('reset-password-view');
    
    if (resetConfirmation && resetForm) {
      resetForm.style.display = 'none';
      resetConfirmation.style.display = 'block';
    }
  } catch (error) {
    handleAuthError(error);
    setButtonState(elements.forgotPasswordBtn, false);
  }
}

// Login user with server
async function loginUser(user, idToken) {
  try {
    const response = await fetch('/auth', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`
      },
      credentials: 'same-origin',
      cache: 'no-store'
    });

    if (!response.ok) {
      throw new Error('Server authentication failed');
    }

    // Clear any stored auth errors
    sessionStorage.removeItem('auth_error');

    // Redirect to dashboard
    window.location.href = '/dashboard';
  } catch (error) {
    console.error('Login error:', error);
    sessionStorage.setItem('auth_error', 'Failed to authenticate with server');
    if (elements.errorMsgGoogleSignIn) {
      elements.errorMsgGoogleSignIn.textContent = "Failed to authenticate. Please try again.";
    }
    
    // Force a new authentication attempt
    await auth.signOut();
  }
}

// Handle authentication errors
function handleAuthError(error) {
  console.error("Auth error:", error);
  
  switch (error.code) {
    case "auth/invalid-email":
      if (elements.errorMsgEmail) elements.errorMsgEmail.textContent = "Invalid email format";
      break;
    case "auth/user-disabled":
      if (elements.errorMsgEmail) elements.errorMsgEmail.textContent = "This account has been disabled";
      break;
    case "auth/user-not-found":
      if (elements.errorMsgEmail) elements.errorMsgEmail.textContent = "No account found with this email";
      break;
    case "auth/wrong-password":
      if (elements.errorMsgPassword) elements.errorMsgPassword.textContent = "Incorrect password";
      break;
    case "auth/email-already-in-use":
      if (elements.errorMsgEmail) elements.errorMsgEmail.textContent = "Email already in use";
      break;
    case "auth/weak-password":
      if (elements.errorMsgPassword) elements.errorMsgPassword.textContent = "Password is too weak";
      break;
    default:
      if (elements.errorMsgEmail) elements.errorMsgEmail.textContent = "An error occurred. Please try again.";
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // Save original button text
  ['signInWithGoogleBtn', 'signUpWithGoogleBtn', 'signInBtn', 'createAccountBtn', 'forgotPasswordBtn'].forEach(btnId => {
    const btn = elements[btnId];
    if (btn) {
      btn.dataset.originalText = btn.textContent;
    }
  });
  
  // Initialize event listeners
  initEventListeners();
  
  // Check for stored auth errors
  const authError = sessionStorage.getItem('auth_error');
  if (authError && elements.errorMsgGoogleSignIn) {
    elements.errorMsgGoogleSignIn.textContent = authError;
    sessionStorage.removeItem('auth_error');
  }
});



