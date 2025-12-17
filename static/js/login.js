// PWA Install Banner Logic
let deferredPrompt;
const pwaBanner = document.getElementById('pwaBanner');
const iosModal = document.getElementById('iosModal');

// Check if already installed
const isInstalled = localStorage.getItem('pwaInstalled') === 'true';

// Detect platform
function getPlatform() {
  const userAgent = navigator.userAgent.toLowerCase();
  if (/iphone|ipad|ipod/.test(userAgent)) {
    return 'ios';
  } else if (/android/.test(userAgent)) {
    return 'android';
  }
  return 'desktop';
}

const platform = getPlatform();

// Show banner if not installed
if (!isInstalled) {
  // For Android/Desktop with beforeinstallprompt support
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    pwaBanner.classList.remove('hidden');
  });
  
  // For iOS or if beforeinstallprompt not fired
  if (platform === 'ios' || (platform === 'android' && !deferredPrompt)) {
    // Show banner after a short delay
    setTimeout(() => {
      pwaBanner.classList.remove('hidden');
    }, 1000);
  }
}

// Handle banner click
pwaBanner.addEventListener('click', async () => {
  if (deferredPrompt) {
    // Android/Desktop with native prompt
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      localStorage.setItem('pwaInstalled', 'true');
      pwaBanner.classList.add('hidden');
    }
    deferredPrompt = null;
  } else {
    // Show instructions modal with appropriate tab
    iosModal.classList.add('show');
    
    // Switch to appropriate tab based on platform
    if (platform === 'android') {
      switchTabProgrammatically('android');
    } else {
      switchTabProgrammatically('ios');
    }
  }
});

// Close iOS modal
function closeIOSModal(installed) {
  iosModal.classList.remove('show');
  if (installed) {
    localStorage.setItem('pwaInstalled', 'true');
    pwaBanner.classList.add('hidden');
  }
}

// Switch between iOS and Android tabs
function switchTab(platform) {
  // Call the programmatic function
  switchTabProgrammatically(platform);
}

// Programmatically switch tabs (without relying on event.target)
function switchTabProgrammatically(platform) {
  const tabs = document.querySelectorAll('.platform-tab');
  const iosContent = document.getElementById('iosContent');
  const androidContent = document.getElementById('androidContent');
  
  tabs.forEach(tab => {
    if ((platform === 'ios' && tab.textContent.includes('iOS')) ||
        (platform === 'android' && tab.textContent.includes('Android'))) {
      tab.classList.add('active');
    } else {
      tab.classList.remove('active');
    }
  });
  
  if (platform === 'ios') {
    iosContent.classList.add('active');
    androidContent.classList.remove('active');
  } else {
    androidContent.classList.add('active');
    iosContent.classList.remove('active');
  }
}

// Close modal on backdrop click
iosModal.addEventListener('click', (e) => {
  if (e.target === iosModal) {
    closeIOSModal(false);
  }
});

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

// Simple form validation and error display
const form = document.getElementById('loginForm');
const errorMessage = document.getElementById('errorMessage');
const submitBtn = document.getElementById('submitBtn');

form.addEventListener('submit', async function(e) {
  e.preventDefault(); // Prevent default form submission
  
  errorMessage.textContent = '';
  submitBtn.disabled = true;
  submitBtn.textContent = 'Accesso...';
  
  const userId = document.getElementById('user_id').value;
  const password = document.getElementById('user_pass').value;
  
  try {
    // Step 1: Login to ClasseViva API from browser
    const loginResponse = await ClasseVivaAPI.login(userId, password);
    const token = loginResponse.token;
    
    if (!token) {
      throw new Error('INVALID_TOKEN');
    }
    
    // Step 2: Store credentials in sessionStorage
    ClasseVivaAPI.storeCredentials(token, userId);
    
    // Step 3: Get grades from ClasseViva API
    const studentId = ClasseVivaAPI.extractStudentId(userId);
    const gradesData = await ClasseVivaAPI.getGrades(studentId, token);
    
    // Step 4: Send grades to backend for session storage
    const backendResponse = await fetch('/api/save_session', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: userId,
        token: token,
        grades: gradesData
      })
    });
    
    if (!backendResponse.ok) {
      throw new Error('BACKEND_ERROR');
    }
    
    // Step 5: Redirect to grades page
    window.location.href = '/grades';
    
  } catch (error) {
    // Re-enable button
    submitBtn.disabled = false;
    submitBtn.textContent = 'Accedi';
    
    // Show appropriate error message
    if (error.message === 'INVALID_CREDENTIALS') {
      errorMessage.textContent = 'Credenziali non valide. Verifica User ID e Password.';
    } else if (error.message.startsWith('HTTP_ERROR_422')) {
      errorMessage.textContent = 'Credenziali non valide. Verifica User ID e Password.';
    } else if (error.message === 'NETWORK_ERROR') {
      errorMessage.textContent = 'Errore di connessione. Verifica la tua connessione internet.';
    } else if (error.message === 'TOKEN_EXPIRED') {
      errorMessage.textContent = 'Sessione scaduta. Riprova.';
    } else if (error.message === 'BACKEND_ERROR') {
      errorMessage.textContent = 'Errore del server. Riprova più tardi.';
    } else {
      errorMessage.textContent = 'Errore imprevisto. Riprova più tardi.';
    }
  }
});

// Register Service Worker for PWA
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(registration => {
        console.log('Service Worker registered successfully:', registration.scope);
      })
      .catch(error => {
        console.log('Service Worker registration failed:', error);
      });
  });
}
