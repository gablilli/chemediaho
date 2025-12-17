// Theme management
const themeToggle = document.getElementById('themeToggle');
const root = document.documentElement;

function getSystemTheme() {
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
    return 'light';
  }
  return 'dark';
}

const savedTheme = localStorage.getItem('theme');
const initialTheme = savedTheme || getSystemTheme();

if (initialTheme === 'light') {
  root.setAttribute('data-theme', 'light');
}

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

// Notification helper
function showNotification(message, type = 'success') {
  const notification = document.getElementById('notification');
  notification.textContent = message;
  notification.className = `notification ${type} show`;
  setTimeout(() => {
    notification.classList.remove('show');
  }, 3000);
}

// Update app button (combines sync and clear cache)
const updateBtn = document.getElementById('updateBtn');
updateBtn.addEventListener('click', async () => {
  updateBtn.classList.add('loading');
  updateBtn.disabled = true;
  
  try {
    // Step 1: Fetch fresh grades from backend (which calls ClasseViva API)
    showNotification('Sincronizzazione voti in corso...', 'info');
    const syncResponse = await fetch('/refresh_grades', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    const syncData = await syncResponse.json();
    
    if (!syncResponse.ok) {
      if (syncData.redirect) {
        window.location.href = syncData.redirect;
        return;
      }
      throw new Error(syncData.error || 'Errore durante la sincronizzazione');
    }
    
    showNotification('Voti sincronizzati! Aggiornamento app...', 'success');
    
    // Step 2: Clear cache
    await new Promise(resolve => setTimeout(resolve, 500));
    
    if ('caches' in window) {
      const cacheNames = await caches.keys();
      await Promise.all(cacheNames.map(name => caches.delete(name)));
    }
    
    // Step 3: Unregister Service Worker
    if ('serviceWorker' in navigator) {
      const registrations = await navigator.serviceWorker.getRegistrations();
      await Promise.all(registrations.map(reg => reg.unregister()));
    }
    
    showNotification('✨ App aggiornata! Ricaricamento...', 'success');
    
    // Reload to apply updates
    setTimeout(() => {
      window.location.href = '/grades';
    }, 1500);
  } catch (error) {
    let errorMessage = error.message || 'Errore durante l\'aggiornamento';
    
    showNotification(errorMessage, 'error');
    updateBtn.classList.remove('loading');
    updateBtn.disabled = false;
  }
});

// Handle logout from bottom nav
const logoutNavBtn = document.getElementById('logoutNavBtn');
if (logoutNavBtn) {
  logoutNavBtn.addEventListener('click', () => {
    // Submit logout form to backend
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/logout';
    document.body.appendChild(form);
    form.submit();
  });
}

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
