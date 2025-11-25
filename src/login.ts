import { initTheme } from './common';

// PWA Install Banner Logic
let deferredPrompt: any;

function getPlatform(): 'ios' | 'android' | 'desktop' {
  const userAgent = navigator.userAgent.toLowerCase();
  if (/iphone|ipad|ipod/.test(userAgent)) {
    return 'ios';
  } else if (/android/.test(userAgent)) {
    return 'android';
  }
  return 'desktop';
}

function closeIOSModal(installed: boolean): void {
  const iosModal = document.getElementById('iosModal');
  if (!iosModal) return;
  
  iosModal.classList.remove('show');
  if (installed) {
    localStorage.setItem('pwaInstalled', 'true');
    const pwaBanner = document.getElementById('pwaBanner');
    if (pwaBanner) {
      pwaBanner.classList.add('hidden');
    }
  }
}

function switchTabProgrammatically(platform: 'ios' | 'android'): void {
  const tabs = document.querySelectorAll('.platform-tab');
  const iosContent = document.getElementById('iosContent');
  const androidContent = document.getElementById('androidContent');

  tabs.forEach(tab => {
    if ((platform === 'ios' && tab.textContent?.includes('iOS')) ||
        (platform === 'android' && tab.textContent?.includes('Android'))) {
      tab.classList.add('active');
    } else {
      tab.classList.remove('active');
    }
  });

  if (platform === 'ios') {
    iosContent?.classList.add('active');
    androidContent?.classList.remove('active');
  } else {
    androidContent?.classList.add('active');
    iosContent?.classList.remove('active');
  }
}

function switchTab(platform: 'ios' | 'android'): void {
  switchTabProgrammatically(platform);
}

function initPWABanner(): void {
  const pwaBanner = document.getElementById('pwaBanner');
  const iosModal = document.getElementById('iosModal');

  if (!pwaBanner || !iosModal) return;

  const isInstalled = localStorage.getItem('pwaInstalled') === 'true';
  const platform = getPlatform();

  if (!isInstalled) {
    window.addEventListener('beforeinstallprompt', (e: Event) => {
      e.preventDefault();
      deferredPrompt = e;
      pwaBanner.classList.remove('hidden');
    });

    if (platform === 'ios' || (platform === 'android' && !deferredPrompt)) {
      setTimeout(() => {
        pwaBanner.classList.remove('hidden');
      }, 1000);
    }
  }

  pwaBanner.addEventListener('click', async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        localStorage.setItem('pwaInstalled', 'true');
        pwaBanner.classList.add('hidden');
      }
      deferredPrompt = null;
    } else {
      iosModal.classList.add('show');
      if (platform === 'android') {
        switchTabProgrammatically('android');
      } else {
        switchTabProgrammatically('ios');
      }
    }
  });

  iosModal.addEventListener('click', (e) => {
    if (e.target === iosModal) {
      closeIOSModal(false);
    }
  });
}

function initLoginForm(): void {
  const form = document.getElementById('loginForm') as HTMLFormElement;
  const errorMessage = document.getElementById('errorMessage');
  const submitBtn = document.getElementById('submitBtn') as HTMLButtonElement;

  if (!form || !errorMessage || !submitBtn) return;

  form.addEventListener('submit', function() {
    errorMessage.textContent = '';
    submitBtn.disabled = true;
    submitBtn.textContent = 'Accesso...';
  });
}

function initServiceWorker(): void {
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
}

// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initPWABanner();
  initLoginForm();
  initServiceWorker();
});

// Export functions for use in HTML onclick attributes
(window as any).closeIOSModal = closeIOSModal;
(window as any).switchTab = switchTab;

