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
      
      // Handle refresh button
      const refreshBtn = document.getElementById('refreshBtn');
      if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
          refreshBtn.classList.add('loading');
          refreshBtn.disabled = true;
          
          try {
            const response = await fetch('/refresh_grades', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
            });
            
            const data = await response.json();
            
            if (response.ok) {
              // Reload page to show updated grades
              window.location.reload();
            } else if (data.redirect) {
              // Session expired, redirect to login
              window.location.href = data.redirect;
            } else {
              alert('Errore durante l\'aggiornamento dei voti: ' + (data.error || 'Errore sconosciuto'));
              refreshBtn.classList.remove('loading');
              refreshBtn.disabled = false;
            }
          } catch (error) {
            alert('Errore di connessione durante l\'aggiornamento dei voti');
            refreshBtn.classList.remove('loading');
            refreshBtn.disabled = false;
          }
        });
      }
    </script>
