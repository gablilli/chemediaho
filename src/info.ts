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

      // Handle logout from bottom nav
      const logoutNavBtn = document.getElementById('logoutNavBtn');
      if (logoutNavBtn) {
        logoutNavBtn.addEventListener('click', () => {
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
    </script>
