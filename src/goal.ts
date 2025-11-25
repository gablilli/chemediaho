      // Store grades data from server
      const gradesData = {{ grades_avr | tojson | safe }};

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

      // Handle period selection
      const periodSelect = document.getElementById('periodSelect');
      const subjectSelect = document.getElementById('subjectSelect');

      // Helper function to show error notification
      function showError(message) {
        const notification = document.getElementById('errorNotification');
        notification.textContent = message;
        notification.classList.add('show');
        setTimeout(() => {
          notification.classList.remove('show');
        }, 3000);
      }

      periodSelect.addEventListener('change', function() {
        const period = this.value;
        subjectSelect.disabled = false;
        subjectSelect.innerHTML = '<option value="">Seleziona una materia...</option>';
        
        if (period && gradesData[period]) {
          const subjects = Object.keys(gradesData[period]).filter(s => s !== 'period_avr');
          subjects.forEach(subject => {
            const option = document.createElement('option');
            option.value = subject;
            option.textContent = subject;
            subjectSelect.appendChild(option);
          });
        } else {
          subjectSelect.disabled = true;
          subjectSelect.innerHTML = '<option value="">Prima seleziona un periodo...</option>';
        }
        
        // Reset target average constraints when period changes
        resetTargetAverageInput();
      });

      // Handle subject selection to update target average constraints
      subjectSelect.addEventListener('change', function() {
        const period = periodSelect.value;
        const subject = this.value;
        
        if (period && subject && gradesData[period] && gradesData[period][subject]) {
          const subjectData = gradesData[period][subject];
          const currentAverage = subjectData.avr || 0;
          
          // Update minimum value for target average input
          const targetInput = document.getElementById('targetAverage');
          const targetRangeLabel = document.getElementById('targetRangeLabel');
          const targetHelp = document.getElementById('targetHelp');
          
          // Use ceiling to ensure minimum target is always higher than current average
          targetInput.min = Math.max(1, Math.ceil(currentAverage * 10) / 10);
          targetRangeLabel.textContent = `(${targetInput.min}-10)`;
          targetHelp.textContent = `La tua media attuale è ${currentAverage.toFixed(2)}. Imposta un obiettivo superiore.`;
          
          // Clear any previously entered value that might be invalid
          if (targetInput.value && parseFloat(targetInput.value) < targetInput.min) {
            targetInput.value = '';
          }
        } else {
          resetTargetAverageInput();
        }
      });

      function resetTargetAverageInput() {
        const targetInput = document.getElementById('targetAverage');
        const targetRangeLabel = document.getElementById('targetRangeLabel');
        const targetHelp = document.getElementById('targetHelp');
        
        targetInput.min = 1;
        targetRangeLabel.textContent = '(1-10)';
        targetHelp.textContent = '';
        targetInput.value = '';
      }

      // Handle form submission
      const goalForm = document.getElementById('goalForm');
      const resultCard = document.getElementById('resultCard');
      const calculateBtn = document.getElementById('calculateBtn');

      goalForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const period = periodSelect.value;
        const subject = subjectSelect.value;
        const targetAverage = parseFloat(document.getElementById('targetAverage').value);

        if (!period || !subject || !targetAverage) {
          showError('Compila tutti i campi!');
          return;
        }

        // Disable button during calculation
        calculateBtn.disabled = true;
        calculateBtn.textContent = 'Calcolo in corso...';

        try {
          const response = await fetch('/calculate_goal', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              period: period,
              subject: subject,
              target_average: targetAverage
            })
          });

          const data = await response.json();

          if (response.ok && data.success) {
            displayResult(data);
          } else {
            showError(data.error || 'Errore durante il calcolo');
          }
        } catch (error) {
          showError('Errore di connessione');
        } finally {
          calculateBtn.disabled = false;
          calculateBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
            Calcola
          `;
        }
      });

      function displayResult(data) {
        // Update result values
        document.getElementById('currentAverage').textContent = data.current_average.toFixed(2);
        document.getElementById('targetAverageDisplay').textContent = data.target_average.toFixed(2);
        document.getElementById('requiredGrade').textContent = data.required_grade.toFixed(2);
        document.getElementById('gradesCount').textContent = data.current_grades_count;
        document.getElementById('resultMessage').textContent = data.message;

        // Set result card style based on achievability
        resultCard.classList.remove('success', 'warning', 'error');
        
        if (data.required_grade < 1) {
          resultCard.classList.add('success');
          document.getElementById('resultEmoji').textContent = '🎉';
          document.getElementById('resultTitle').textContent = 'Fantastico!';
        } else if (data.required_grade > 10) {
          resultCard.classList.add('error');
          document.getElementById('resultEmoji').textContent = '😅';
          document.getElementById('resultTitle').textContent = 'Difficile...';
        } else if (data.required_grade >= 9) {
          resultCard.classList.add('warning');
          document.getElementById('resultEmoji').textContent = '💪';
          document.getElementById('resultTitle').textContent = 'Impegnati!';
        } else if (data.required_grade >= 7) {
          resultCard.classList.add('success');
          document.getElementById('resultEmoji').textContent = '👍';
          document.getElementById('resultTitle').textContent = 'Fattibile!';
        } else {
          resultCard.classList.add('success');
          document.getElementById('resultEmoji').textContent = '✅';
          document.getElementById('resultTitle').textContent = 'Ottimo!';
        }

        // Show result card
        resultCard.classList.add('show');
        
        // Scroll to result
        resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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
    </script>
