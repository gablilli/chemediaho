// Theme management
const themeToggle = document.getElementById('themeToggle');
const root = document.documentElement;

// Function to get system preference
function getSystemTheme() {
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
    return 'light';
  }
  return 'dark';
}

// Load saved theme or use system preference
const savedTheme = localStorage.getItem('theme');
const initialTheme = savedTheme || getSystemTheme();

if (initialTheme === 'light') {
  root.setAttribute('data-theme', 'light');
}

// Toggle theme
themeToggle.addEventListener('click', () => {
  const currentTheme = root.getAttribute('data-theme');
  const newTheme = currentTheme === 'light' ? 'dark' : 'light';
  
  if (newTheme === 'light') {
    root.setAttribute('data-theme', 'light');
  } else {
    root.removeAttribute('data-theme');
  }
  
  localStorage.setItem('theme', newTheme);
});

// Animate circle progress bars
function animateCircle(circle) {
  const target = parseFloat(circle.getAttribute('data-target'));
  const circumference = 327; // 2 * PI * r where r = 52
  
  // Start from full (no progress)
  circle.style.strokeDashoffset = circumference;
  
  // Animate to target
  setTimeout(() => {
    circle.style.strokeDashoffset = circumference - target;
  }, 100);
}

// Animate all circles on page load
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.circle-progress-fill[data-target]').forEach(circle => {
    animateCircle(circle);
  });
});

function showModal(gradeData) {
  const modal = document.getElementById('gradeModal');
  const modalBody = document.getElementById('modalBody');
  
  // Build modal content dynamically for consistency with subject_detail.js
  let html = `
    <p><strong>Voto:</strong> <span style="font-weight: bold; font-size: 18px;">${gradeData.decimalValue}</span></p>
    <p><strong>Data:</strong> ${gradeData.evtDate || 'N/D'}</p>
    <p><strong>Componente:</strong> ${gradeData.componentDesc || 'N/D'}</p>
  `;
  
  if (gradeData.teacherName) {
    html += `<p><strong>Docente:</strong> ${gradeData.teacherName}</p>`;
  }
  
  if (gradeData.notesForFamily) {
    html += `<p><strong>Note:</strong> ${gradeData.notesForFamily}</p>`;
  } else {
    html += `<p><strong>Note:</strong> Nessuna nota</p>`;
  }
  
  if (gradeData.isBlue) {
    html += `<p><strong>Tipo:</strong> <span style="color: #2196F3;">Voto Blu</span></p>`;
  }
  
  modalBody.innerHTML = html;
  modal.classList.add('show');
}

function closeModal() {
  document.getElementById('gradeModal').classList.remove('show');
}

// Close modal when clicking outside
document.getElementById('gradeModal').addEventListener('click', function(e) {
  if (e.target === this) {
    closeModal();
  }
});

// Close modal with Escape key
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    closeModal();
  }
});

// Register Service Worker for PWA
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    // Use API_BASE for service worker registration if configured
    const swUrl = window.APP_CONFIG && window.APP_CONFIG.API_BASE 
      ? `${window.APP_CONFIG.API_BASE}/sw.js` 
      : '/sw.js';
    navigator.serviceWorker.register(swUrl)
      .then(registration => {
        console.log('Service Worker registered successfully:', registration.scope);
      })
      .catch(error => {
        console.log('Service Worker registration failed:', error);
      });
  });
}

// Helper function for logout via apiFetch
async function performLogout() {
  try {
    await apiFetch('/logout', { method: 'POST' });
    apiNavigate('/');
  } catch (error) {
    console.error('Logout error:', error);
    apiNavigate('/');
  }
}

// Handle logout from bottom nav
const logoutNavBtn = document.getElementById('logoutNavBtn');
if (logoutNavBtn) {
  logoutNavBtn.addEventListener('click', performLogout);
}

// Handle logout from top button
const logoutBtn = document.getElementById('logoutBtn');
if (logoutBtn) {
  logoutBtn.addEventListener('click', performLogout);
}
