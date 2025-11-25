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

      function showModal(gradeData) {
        document.getElementById('modalGrade').textContent = gradeData.decimalValue;
        document.getElementById('modalDate').textContent = gradeData.evtDate;
        document.getElementById('modalComponent').textContent = gradeData.componentDesc;
        document.getElementById('modalTeacher').textContent = gradeData.teacherName;
        document.getElementById('modalNotes').textContent = gradeData.notesForFamily || 'Nessuna nota';
        document.getElementById('gradeModal').classList.add('show');
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
          navigator.serviceWorker.register('/sw.js')
            .then(registration => {
              console.log('Service Worker registered successfully:', registration.scope);
            })
            .catch(error => {
              console.log('Service Worker registration failed:', error);
            });
        });
      }

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
