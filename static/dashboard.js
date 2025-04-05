import { getAuth, onAuthStateChanged, signOut } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-auth.js";
import { auth } from "./firebase-config.js";

// Cache DOM elements
let userGreeting, logoutBtn, hamburger, navLinks;
let statElements = {};

// Initialize UI elements and event listeners
function initUI() {
  userGreeting = document.getElementById('username');
  logoutBtn = document.getElementById('logout-btn');
  hamburger = document.querySelector('.hamburger');
  navLinks = document.querySelector('.nav-links');

  // Cache stat elements
  ['measurements_converted', 'recipes_generated', 'tutorials_watched'].forEach(stat => {
    statElements[stat] = document.querySelector(`[data-stat="${stat}"]`);
  });

  // Handle mobile menu toggle
  if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
      navLinks.classList.toggle('active');
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (!e.target.matches('.hamburger') && 
          !e.target.closest('.hamburger') && 
          !e.target.closest('.nav-links') && 
          navLinks.classList.contains('active')) {
        navLinks.classList.remove('active');
      }
    });
  }

  // Handle logout
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
  }

  // Add visible class to animate elements
  document.querySelectorAll('.animate-fade-in').forEach(el => {
    el.classList.add('visible');
  });

  // Start periodic stats update
  updateStats();
  setInterval(updateStats, 30000); // Update every 30 seconds
}

// Handle authentication state changes
function handleAuthState(user) {
  if (user) {
    // User is signed in
    if (userGreeting) {
      userGreeting.textContent = user.displayName || user.email || 'Welcome!';
    }
    
    // Ping server to keep session alive
    keepSessionAlive();
  } else {
    // User is signed out, redirect to login
    window.location.href = '/login';
  }
}

// Keep server session alive
async function keepSessionAlive() {
  try {
    // Simple ping to keep session alive
    const response = await fetch('/dashboard', {
      method: 'HEAD',
      credentials: 'same-origin',
      cache: 'no-store'
    });
    
    // Schedule next ping (every 5 minutes)
    setTimeout(keepSessionAlive, 5 * 60 * 1000);
  } catch (error) {
    console.error('Session ping error:', error);
  }
}

// Handle logout with proper sequence
async function handleLogout(e) {
  e.preventDefault();
  
  try {
    // Disable the logout button to prevent multiple clicks
    if (logoutBtn) {
      logoutBtn.disabled = true;
      logoutBtn.textContent = 'Logging out...';
    }
    
    // First call the server logout endpoint
    const response = await fetch('/logout', {
      method: 'GET',
      credentials: 'same-origin',
      cache: 'no-store'
    });
    
    // Then sign out from Firebase
    await signOut(auth);
    
    // Clear any local storage data
    localStorage.removeItem('firebase:previous_emulator_url');
    localStorage.removeItem('firebase:host:flask-demo-59926-default-rtdb.firebaseio.com');
    
    // Redirect to login page
    window.location.href = '/login';
  } catch (error) {
    console.error('Logout error:', error);
    // Force redirect even if there's an error
    window.location.href = '/';
  }
}

// Function to update stats
async function updateStats() {
  try {
    const response = await fetch('/validate_session', {
      method: 'POST',
      credentials: 'same-origin'
    });
    
    if (!response.ok) {
      throw new Error('Session validation failed');
    }
    
    const data = await response.json();
    if (data.stats) {
      Object.entries(data.stats).forEach(([stat, value]) => {
        const element = document.querySelector(`[data-stat="${stat}"]`);
        if (element) {
          // Animate the number change
          animateNumber(element, parseInt(element.textContent), value);
        }
      });
    }
  } catch (error) {
    console.error('Error updating stats:', error);
  }
}

// Animate number changes
function animateNumber(element, start, end) {
  if (start === end) return;
  
  const duration = 1000; // 1 second
  const steps = 60;
  const step = (end - start) / steps;
  let current = start;
  let count = 0;
  
  const timer = setInterval(() => {
    count++;
    current += step;
    if (count >= steps) {
      clearInterval(timer);
      current = end;
    }
    element.textContent = Math.round(current);
  }, duration / steps);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // Initialize UI
  initUI();
  
  // Listen for authentication state changes
  onAuthStateChanged(auth, handleAuthState);
});