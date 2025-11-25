// Common utility functions shared across all pages

// Theme management
export function getSystemTheme(): 'light' | 'dark' {
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
    return 'light';
  }
  return 'dark';
}

export function initTheme(): void {
  const themeToggle = document.getElementById('themeToggle');
  const root = document.documentElement;

  if (!themeToggle) return;

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
}

// Logout handler
export function initLogout(): void {
  const logoutNavBtn = document.getElementById('logoutNavBtn');
  
  if (logoutNavBtn) {
    logoutNavBtn.addEventListener('click', () => {
      fetch('/logout', { method: 'POST' })
        .then(() => {
          window.location.href = '/';
        })
        .catch((error) => {
          console.error('Logout failed:', error);
          window.location.href = '/';
        });
    });
  }
}

// Refresh button handler
export function initRefresh(callback?: () => void): void {
  const refreshBtn = document.getElementById('refreshBtn');
  
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      const btnElement = refreshBtn as HTMLButtonElement;
      btnElement.disabled = true;
      refreshBtn.textContent = '⏳ Aggiornamento...';

      try {
        if (callback) {
          await callback();
        } else {
          window.location.reload();
        }
      } catch (error) {
        console.error('Refresh failed:', error);
        alert('Errore durante l\'aggiornamento. Riprova.');
      } finally {
        btnElement.disabled = false;
        refreshBtn.textContent = '🔄 Aggiorna';
      }
    });
  }
}
