// Store grades data
const gradesData = {{ grades_avr | tojson }};
const subjectName = {{ subject_name | tojson }};

// Create time series chart for subject grades
function createGradesTrendChart() {
  const ctx = document.getElementById('gradesTrendChart');
  if (!ctx) return;

  // Get theme colors
  const root = document.documentElement;
  const isDark = root.getAttribute('data-theme') !== 'light';
  const textColor = isDark ? '#f1e4e4' : '#1a0a0a';
  const gridColor = isDark ? 'rgba(241, 228, 228, 0.1)' : 'rgba(26, 10, 10, 0.1)';

  // Prepare data from all periods for this subject
  const allGrades = [];
  const labels = [];
  
  const periods = Object.keys(gradesData).filter(key => key !== 'all_avr').sort();
  
  periods.forEach(period => {
    if (gradesData[period][subjectName]) {
      const periodGrades = gradesData[period][subjectName].grades;
      periodGrades.forEach((grade, index) => {
        allGrades.push(grade.decimalValue);
        labels.push(`P${period} V${index + 1}`);
      });
    }
  });

  // Calculate running average
  const runningAvg = [];
  let sum = 0;
  allGrades.forEach((grade, index) => {
    sum += grade;
    runningAvg.push(sum / (index + 1));
  });

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Voti',
          data: allGrades,
          borderColor: '#4facfe',
          backgroundColor: 'rgba(79, 172, 254, 0.1)',
          tension: 0.3,
          fill: true,
          pointRadius: 5,
          pointHoverRadius: 7
        },
        {
          label: 'Media Progressive',
          data: runningAvg,
          borderColor: '#f03333',
          backgroundColor: 'rgba(240, 51, 51, 0.05)',
          borderDash: [5, 5],
          tension: 0.3,
          fill: false,
          pointRadius: 3,
          pointHoverRadius: 5
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            color: textColor,
            usePointStyle: true,
            padding: 15
          }
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: isDark ? 'rgba(19, 9, 9, 0.9)' : 'rgba(254, 248, 248, 0.9)',
          titleColor: textColor,
          bodyColor: textColor,
          borderColor: gridColor,
          borderWidth: 1
        }
      },
      scales: {
        y: {
          beginAtZero: false,
          min: 3,
          max: 10,
          ticks: {
            color: textColor,
            stepSize: 1
          },
          grid: {
            color: gridColor
          }
        },
        x: {
          ticks: {
            color: textColor,
            maxRotation: 45,
            minRotation: 45
          },
          grid: {
            color: gridColor
          }
        }
      }
    }
  });
}

// Initialize chart after page load
document.addEventListener('DOMContentLoaded', () => {
  createGradesTrendChart();
});

// Goal persistence functions
function saveGoal(subject, period, targetAverage, resultData) {
  const goals = JSON.parse(localStorage.getItem('subjectGoals') || '{}');
  goals[subject] = {
    period: period,
    targetAverage: targetAverage,
    currentAverage: resultData.current_average,
    requiredGrade: resultData.required_grade,
    timestamp: new Date().toISOString(),
    achievable: resultData.achievable
  };
  localStorage.setItem('subjectGoals', JSON.stringify(goals));
  displaySavedGoal();
}

function loadSavedGoal() {
  const goals = JSON.parse(localStorage.getItem('subjectGoals') || '{}');
  return goals[subjectName];
}

// Helper to escape HTML special characters
function escapeHTML(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function displaySavedGoal() {
  const goal = loadSavedGoal();
  const savedGoalDisplay = document.getElementById('savedGoalDisplay');
  const savedGoalContent = document.getElementById('savedGoalContent');
  const goalForm = document.getElementById('goalForm');
  
  if (goal) {
    const date = new Date(goal.timestamp).toLocaleDateString('it-IT');
    savedGoalContent.innerHTML = `
      <div style="margin-bottom: 4px;"><strong>Periodo:</strong> ${escapeHTML(goal.period)}</div>
      <div style="margin-bottom: 4px;"><strong>Obiettivo:</strong> ${goal.targetAverage.toFixed(1)}</div>
      <div style="margin-bottom: 4px;"><strong>Voto necessario:</strong> ${goal.requiredGrade.toFixed(2)}</div>
      <div style="margin-bottom: 4px;"><strong>Media attuale:</strong> ${goal.currentAverage.toFixed(2)}</div>
      <div style="font-size: 12px; opacity: 0.7; margin-top: 8px;">Salvato il ${date}</div>
    `;
    savedGoalDisplay.style.display = 'block';
    goalForm.style.display = 'none';
  } else {
    savedGoalDisplay.style.display = 'none';
    goalForm.style.display = 'block';
  }
}

function clearSavedGoal() {
  const goals = JSON.parse(localStorage.getItem('subjectGoals') || '{}');
  delete goals[subjectName];
  localStorage.setItem('subjectGoals', JSON.stringify(goals));
  displaySavedGoal();
}

// Display saved goal on page load
displaySavedGoal();

// Goal form handler
const goalForm = document.getElementById('goalForm');
const calculateBtn = document.getElementById('calculateBtn');
const resultCard = document.getElementById('resultCard');

goalForm.addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const period = document.getElementById('periodSelect').value;
  const targetAverage = parseFloat(document.getElementById('targetAverage').value);
  const numGrades = parseInt(document.getElementById('numGrades').value);
  
  if (!period || !targetAverage || !numGrades) {
    showError('Compila tutti i campi!');
    return;
  }

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
        subject: subjectName,
        target_average: targetAverage,
        num_grades: numGrades
      })
    });

    const data = await response.json();

    if (response.ok && data.success) {
      displayResult(data);
      // Save goal to localStorage
      saveGoal(subjectName, period, targetAverage, data);
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
  document.getElementById('currentAverage').textContent = data.current_average.toFixed(2);
  document.getElementById('targetAverageDisplay').textContent = data.target_average.toFixed(2);
  
  if (data.required_grades && Array.isArray(data.required_grades)) {
    document.getElementById('requiredGrades').textContent = data.required_grades.map(g => g.toFixed(2)).join(', ');
  } else {
    document.getElementById('requiredGrades').textContent = data.required_grade.toFixed(2);
  }
  
  document.getElementById('resultMessage').textContent = data.message || '';
  resultCard.classList.add('show');
  resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showModal(gradeData) {
  const modal = document.getElementById('gradeModal');
  const modalBody = document.getElementById('modalBody');
  
  let html = `
    <div class="modal-detail">
      <span>Voto</span>
      <span style="font-weight: bold; font-size: 18px;">${gradeData.decimalValue}</span>
    </div>
    <div class="modal-detail">
      <span>Descrizione</span>
      <span>${gradeData.componentDesc || 'N/D'}</span>
    </div>
    <div class="modal-detail">
      <span>Data</span>
      <span>${gradeData.evtDate || 'N/D'}</span>
    </div>
  `;
  
  if (gradeData.notesForFamily) {
    html += `
      <div class="modal-detail">
        <span>Note</span>
        <span>${gradeData.notesForFamily}</span>
      </div>
    `;
  }
  
  if (gradeData.isBlue) {
    html += `
      <div class="modal-detail">
        <span>Tipo</span>
        <span style="color: #2196F3;">Voto Blu</span>
      </div>
    `;
  }
  
  modalBody.innerHTML = html;
  modal.style.display = 'block';
}

function closeModal() {
  document.getElementById('gradeModal').style.display = 'none';
}

window.onclick = function(event) {
  const modal = document.getElementById('gradeModal');
  if (event.target == modal) {
    modal.style.display = 'none';
  }
}

function showError(message) {
  const notification = document.getElementById('errorNotification');
  notification.textContent = message;
  notification.classList.add('show');
  
  setTimeout(() => {
    notification.classList.remove('show');
  }, 3000);
}

// Predictions form handler
const predictionsForm = document.getElementById('predictionsForm');
const predictBtn = document.getElementById('predictBtn');
const predictionResult = document.getElementById('predictionResult');

if (predictionsForm) {
  predictionsForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const period = document.getElementById('predictPeriod').value;
    const gradesInput = document.getElementById('predictGrades').value;
    
    // Parse grades
    const predictedGrades = gradesInput.split(',').map(g => parseFloat(g.trim())).filter(g => !isNaN(g) && g >= 1 && g <= 10);
    
    if (predictedGrades.length === 0) {
      showError('Inserisci almeno un voto valido (1-10)!');
      return;
    }

    predictBtn.disabled = true;
    predictBtn.textContent = 'Calcolo in corso...';

    try {
      const response = await fetch('/predict_average', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          period: period,
          subject: subjectName,
          predicted_grades: predictedGrades
        })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        displayPrediction(data);
      } else {
        showError(data.error || 'Errore durante il calcolo');
      }
    } catch (error) {
      showError('Errore di connessione');
    } finally {
      predictBtn.disabled = false;
      predictBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
        </svg>
        Simula
      `;
    }
  });
}

function displayPrediction(data) {
  const predictionContent = document.getElementById('predictionContent');
  predictionContent.innerHTML = '';
  
  const rows = [
    { label: 'Media Attuale', value: data.current_average },
    { label: 'Media Prevista', value: data.predicted_average, highlight: true },
    { label: 'Variazione', value: (data.change >= 0 ? '+' : '') + data.change, highlight: true },
    { label: 'Voti Simulati', value: data.num_predicted_grades }
  ];
  
  rows.forEach(row => {
    const rowEl = document.createElement('div');
    rowEl.className = 'result-row';
    rowEl.innerHTML = `
      <span class="result-label">${row.label}</span>
      <span class="result-value ${row.highlight ? 'highlight' : ''}">${row.value}</span>
    `;
    predictionContent.appendChild(rowEl);
  });
  
  document.getElementById('predictionMessage').textContent = data.message || '';
  predictionResult.classList.add('show');
  predictionResult.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
