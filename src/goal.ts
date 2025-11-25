import { initTheme, initLogout } from './common';

// Simple HTML escaper for output encoding to prevent XSS
function escapeHTML(str: string): string {
  return str.replace(/[&<>"'`]/g, function (c) {
    return ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
     '"': '&quot;',
     "'": '&#39;',
     '`': '&#96;',
    } as { [k: string]: string })[c] || c;
  });
}

// Initialize goal calculator
function initGoalCalculator(gradesData: any): void {
  const form = document.getElementById('goalForm') as HTMLFormElement;
  const subjectSelect = document.getElementById('subjectSelect') as HTMLSelectElement;
  const targetInput = document.getElementById('targetAverage') as HTMLInputElement;
  const calculateBtn = document.getElementById('calculateBtn') as HTMLButtonElement;
  const resultDiv = document.getElementById('result');

  if (!form || !subjectSelect || !targetInput || !calculateBtn || !resultDiv) return;

  // Populate subject dropdown
  const subjects = new Set<string>();
  Object.keys(gradesData).forEach(period => {
    if (period !== 'all_avr') {
      Object.keys(gradesData[period]).forEach(subject => {
        if (subject !== 'period_avr') {
          subjects.add(subject);
        }
      });
    }
  });

  subjects.forEach(subject => {
    const option = document.createElement('option');
    option.value = subject;
    option.textContent = subject;
    subjectSelect.appendChild(option);
  });

  // Calculate required grade
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const subject = subjectSelect.value;
    const targetAverage = parseFloat(targetInput.value);

    if (!subject || isNaN(targetAverage)) {
      resultDiv.innerHTML = '<p class="error">⚠️ Seleziona una materia e inserisci una media target valida.</p>';
      return;
    }

    // Get current grades for subject
    const grades: number[] = [];
    Object.keys(gradesData).forEach(period => {
      if (period !== 'all_avr') {
        const grade = gradesData[period][subject];
        if (typeof grade === 'number') {
          grades.push(grade);
        }
      }
    });

    if (grades.length === 0) {
      resultDiv.innerHTML = '<p class="error">⚠️ Nessun voto disponibile per questa materia.</p>';
      return;
    }

    const currentSum = grades.reduce((a, b) => a + b, 0);
    const currentAverage = currentSum / grades.length;
    const requiredGrade = targetAverage * (grades.length + 1) - currentSum;

    let resultHTML = `
      <h3>📊 Risultato</h3>
      <div class="result-info">
        <p><strong>Materia:</strong> ${escapeHTML(subject)}</p>
        <p><strong>Media attuale:</strong> ${currentAverage.toFixed(2)}</p>
        <p><strong>Numero voti:</strong> ${grades.length}</p>
        <p><strong>Media target:</strong> ${targetAverage.toFixed(2)}</p>
      </div>
    `;

    if (requiredGrade < 0 || requiredGrade > 10) {
      resultHTML += '<p class="error">⚠️ Impossibile raggiungere questa media con un solo voto.</p>';
    } else {
      const message = requiredGrade < 6 
        ? '🎉 Congratulazioni! Puoi raggiungere la tua media target!'
        : requiredGrade > 10
        ? '😅 Serve un voto superiore al massimo!'
        : `✅ Devi prendere <strong>${requiredGrade.toFixed(2)}</strong> al prossimo voto!`;
      
      resultHTML += `<p class="success">${message}</p>`;
    }

    resultDiv.innerHTML = resultHTML;
  });

  // Min target validation
  targetInput.addEventListener('input', () => {
    if (parseFloat(targetInput.value) < parseFloat(targetInput.min)) {
      targetInput.value = targetInput.min;
    }
  });
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initLogout();
  
  // Get grades data from window object (injected by backend)
  const gradesData = (window as any).gradesData;
  if (gradesData) {
    initGoalCalculator(gradesData);
  }
});
