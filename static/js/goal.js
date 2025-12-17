// Store grades data from server (injected by template)
const gradesData = window.gradesData || [];

// Track number of grades for goal calculator
let numGradesGoal = 1;
let numGradesPredict = 1;
let numGradesOverallGoal = 1;
let numGradesOverallPredict = 1;

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

// Tab switching
function switchTab(tabName) {
  // Hide all tabs
  document.getElementById('goalTab').classList.remove('active');
  document.getElementById('predictTab').classList.remove('active');
  document.getElementById('overallTab').classList.remove('active');
  
  // Deactivate all tab buttons
  const tabButtons = document.querySelectorAll('.tabs-container .tab-button');
  tabButtons.forEach(btn => btn.classList.remove('active'));
  
  // Show selected tab
  if (tabName === 'overall') {
    document.getElementById('overallTab').classList.add('active');
    tabButtons[0].classList.add('active');
  } else if (tabName === 'goal') {
    document.getElementById('goalTab').classList.add('active');
    tabButtons[1].classList.add('active');
  } else if (tabName === 'predict') {
    document.getElementById('predictTab').classList.add('active');
    tabButtons[2].classList.add('active');
  }
}

// Helper function to show error notification
function showError(message) {
  const notification = document.getElementById('errorNotification');
  notification.textContent = message;
  notification.classList.add('show');
  setTimeout(() => {
    notification.classList.remove('show');
  }, 3000);
}

// Helper function for Italian pluralization of "voto"
function pluralizeVoto(count) {
  return count === 1 ? 'voto' : 'voti';
}

// Helper function for Italian pluralization of "voto attuale"
function pluralizeCurrentGrades(count) {
  return count === 1 ? 'voto attuale' : 'voti attuali';
}

// Add grade input for goal calculator
function addGradeInput() {
  numGradesGoal++;
  const container = document.getElementById('gradesInputContainer');
  const gradeGroup = document.createElement('div');
  gradeGroup.className = 'grade-input-group';
  gradeGroup.innerHTML = `
    <span style="font-size: 14px; opacity: 0.8;">${numGradesGoal} ${pluralizeVoto(numGradesGoal)}</span>
    <button type="button" class="remove-grade-btn" onclick="removeGradeInput(this)">×</button>
  `;
  container.appendChild(gradeGroup);
}

function removeGradeInput(btn) {
  if (numGradesGoal > 1) {
    btn.parentElement.remove();
    numGradesGoal--;
    // Update labels
    const groups = document.querySelectorAll('#gradesInputContainer .grade-input-group');
    groups.forEach((group, index) => {
      const span = group.querySelector('span');
      if (span) {
        span.textContent = `${index + 1} ${pluralizeVoto(index + 1)}`;
      }
    });
  }
}

// Add grade input for predict calculator
function addPredictGradeInput() {
  numGradesPredict++;
  const container = document.getElementById('predictGradesContainer');
  const gradeGroup = document.createElement('div');
  gradeGroup.className = 'grade-input-group';
  gradeGroup.innerHTML = `
    <input 
      type="number" 
      class="grade-input-small predict-grade-input" 
      min="1" 
      max="10" 
      step="0.5" 
      placeholder="Voto"
      required
    />
    <button type="button" class="remove-grade-btn" onclick="removePredictGradeInput(this)">×</button>
  `;
  container.appendChild(gradeGroup);
}

function removePredictGradeInput(btn) {
  if (numGradesPredict > 1) {
    btn.parentElement.remove();
    numGradesPredict--;
  }
}

// Handle period selection for Goal
const periodSelectGoal = document.getElementById('periodSelectGoal');
const subjectSelectGoal = document.getElementById('subjectSelectGoal');

periodSelectGoal.addEventListener('change', function() {
  const period = this.value;
  subjectSelectGoal.disabled = false;
  subjectSelectGoal.innerHTML = '<option value="">Seleziona una materia...</option>';
  
  if (period && gradesData[period]) {
    const subjects = Object.keys(gradesData[period]).filter(s => s !== 'period_avr');
    subjects.forEach(subject => {
      const option = document.createElement('option');
      option.value = subject;
      option.textContent = subject;
      subjectSelectGoal.appendChild(option);
    });
    // Enable required validation when subject select is enabled
    subjectSelectGoal.required = true;
  } else {
    subjectSelectGoal.disabled = true;
    subjectSelectGoal.required = false;
    subjectSelectGoal.innerHTML = '<option value="">Prima seleziona un periodo...</option>';
  }
  
  updateTargetAverageInputGoal();
});

// Handle subject selection to update target average constraints
subjectSelectGoal.addEventListener('change', function() {
  updateTargetAverageInputGoal();
});

function updateTargetAverageInputGoal() {
  const period = periodSelectGoal.value;
  const subject = subjectSelectGoal.value;
  const targetInput = document.getElementById('targetAverage');
  const targetRangeLabel = document.getElementById('targetRangeLabel');
  const targetHelp = document.getElementById('targetHelp');
  
  if (period && gradesData[period]) {
    // Calculate period average to use as minimum
    const periodAvg = gradesData[period].period_avr || 0;
    
    if (subject && gradesData[period][subject]) {
      const subjectData = gradesData[period][subject];
      const currentAverage = subjectData.avr || 0;
      
      targetInput.min = Math.max(1, Math.ceil(currentAverage * 10) / 10);
      targetRangeLabel.textContent = `(${targetInput.min}-10)`;
      targetHelp.textContent = `La tua media attuale in ${subject} è ${currentAverage.toFixed(2)}. Imposta un obiettivo superiore.`;
    } else {
      // No subject selected, use period average
      targetInput.min = Math.max(1, Math.ceil(periodAvg * 10) / 10);
      targetRangeLabel.textContent = `(${targetInput.min}-10)`;
      targetHelp.textContent = `La media del periodo ${period} è ${periodAvg.toFixed(2)}. Imposta un obiettivo superiore.`;
    }
    
    if (targetInput.value && parseFloat(targetInput.value) < targetInput.min) {
      targetInput.value = '';
    }
  } else {
    targetInput.min = 1;
    targetRangeLabel.textContent = '(1-10)';
    targetHelp.textContent = '';
    targetInput.value = '';
  }
}

// Handle period selection for Predict
const periodSelectPredict = document.getElementById('periodSelectPredict');
const subjectSelectPredict = document.getElementById('subjectSelectPredict');

periodSelectPredict.addEventListener('change', function() {
  const period = this.value;
  subjectSelectPredict.disabled = false;
  subjectSelectPredict.innerHTML = '<option value="">Seleziona una materia...</option>';
  
  if (period && gradesData[period]) {
    const subjects = Object.keys(gradesData[period]).filter(s => s !== 'period_avr');
    subjects.forEach(subject => {
      const option = document.createElement('option');
      option.value = subject;
      option.textContent = subject;
      subjectSelectPredict.appendChild(option);
    });
  } else {
    subjectSelectPredict.disabled = true;
    subjectSelectPredict.innerHTML = '<option value="">Prima seleziona un periodo...</option>';
  }
});

// Handle goal form submission
const goalForm = document.getElementById('goalForm');
const resultCardGoal = document.getElementById('resultCardGoal');
const calculateBtnGoal = document.getElementById('calculateBtnGoal');

// Smart suggestion function for Goal tab
async function getSmartSuggestionGoal() {
  const period = periodSelectGoal.value;
  const targetAverage = parseFloat(document.getElementById('targetAverage').value);

  if (!period || !targetAverage) {
    showError('Seleziona un periodo e inserisci una media target!');
    return;
  }

  const smartBtn = document.getElementById('smartSuggestBtnGoal');
  smartBtn.disabled = true;
  smartBtn.textContent = 'Calcolo in corso...';

  // Hide other result cards
  resultCardGoal.classList.remove('show');

  try {
    const response = await fetch('/calculate_goal', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        period: period,
        target_average: targetAverage,
        num_grades: numGradesGoal
        // No subject - triggers smart suggestions
      })
    });

    const data = await response.json();

    if (response.ok && data.success) {
      displaySmartSuggestionsGoal(data);
    } else {
      showError(data.error || 'Errore durante il calcolo');
    }
  } catch (error) {
    showError('Errore di connessione');
  } finally {
    smartBtn.disabled = false;
    smartBtn.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      🎯 Suggerimenti Intelligenti
    `;
  }
}

function displaySmartSuggestionsGoal(data) {
  const resultCard = document.getElementById('resultCardSmartSuggestionsGoal');
  
  document.getElementById('periodSmartGoal').textContent = `Periodo ${data.period}`;
  document.getElementById('targetAverageSmartGoal').textContent = data.target_average.toFixed(2);
  
  const suggestionsContainer = document.getElementById('suggestionsContainerGoal');
  suggestionsContainer.innerHTML = '';
  
  if (data.suggestions && data.suggestions.length > 0) {
    const header = document.createElement('h3');
    header.style.fontSize = '16px';
    header.style.fontWeight = 'bold';
    header.style.marginBottom = '12px';
    header.style.color = 'var(--text)';
    header.textContent = '📚 Materie Consigliate (ordinate per facilità):';
    suggestionsContainer.appendChild(header);
    
    data.suggestions.forEach((suggestion, index) => {
      const suggestionItem = document.createElement('div');
      suggestionItem.className = 'suggestion-item';
      
      const rank = index + 1;
      const emoji = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '📌';
      
      suggestionItem.innerHTML = `
        <div class="subject-name">${emoji} ${suggestion.subject}</div>
        <div class="suggestion-details">
          <span>Media attuale: ${suggestion.current_average}</span>
          <span class="required-grade">Voto necessario: ${suggestion.required_grade}</span>
        </div>
        <div style="font-size: 12px; margin-top: 4px; opacity: 0.7;">
          ${suggestion.num_current_grades} ${pluralizeCurrentGrades(suggestion.num_current_grades)}
        </div>
      `;
      
      suggestionsContainer.appendChild(suggestionItem);
    });
  } else {
    suggestionsContainer.innerHTML = '<p style="opacity: 0.7;">Nessun suggerimento disponibile.</p>';
  }
  
  document.getElementById('resultMessageSmartGoal').textContent = data.message;
  
  resultCard.classList.add('show');
  resultCard.style.display = 'block';
  resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

goalForm.addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const period = periodSelectGoal.value;
  const subject = subjectSelectGoal.value;
  const targetAverage = parseFloat(document.getElementById('targetAverage').value);

  if (!period || !subject || !targetAverage) {
    showError('Seleziona una materia e inserisci una media target!');
    return;
  }

  calculateBtnGoal.disabled = true;
  calculateBtnGoal.textContent = 'Calcolo in corso...';

  // Hide smart suggestions card
  document.getElementById('resultCardSmartSuggestionsGoal').classList.remove('show');
  document.getElementById('resultCardSmartSuggestionsGoal').style.display = 'none';

  try {
    const response = await fetch('/calculate_goal', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        period: period,
        subject: subject,
        target_average: targetAverage,
        num_grades: numGradesGoal
      })
    });

    const data = await response.json();

    if (response.ok && data.success) {
      displayGoalResult(data);
    } else {
      showError(data.error || 'Errore durante il calcolo');
    }
  } catch (error) {
    showError('Errore di connessione');
  } finally {
    calculateBtnGoal.disabled = false;
    calculateBtnGoal.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
      </svg>
      Calcola per Materia Specifica
    `;
  }
});

function displayGoalResult(data) {
  document.getElementById('currentAverageGoal').textContent = data.current_average.toFixed(2);
  document.getElementById('targetAverageDisplay').textContent = data.target_average.toFixed(2);
  
  // Display required grades (use 2 decimal places for consistency)
  const requiredGradesEl = document.getElementById('requiredGradesGoal');
  if (data.required_grades && Array.isArray(data.required_grades)) {
    requiredGradesEl.textContent = data.required_grades.map(g => g.toFixed(2)).join(', ');
  } else {
    requiredGradesEl.textContent = data.required_grade.toFixed(2);
  }
  
  document.getElementById('resultMessageGoal').textContent = data.message;

  // Set result card style
  resultCardGoal.classList.remove('success', 'warning', 'error');
  
  const avgGrade = data.required_grades ? 
    data.required_grades.reduce((a, b) => a + b, 0) / data.required_grades.length : 
    data.required_grade;
  
  if (avgGrade < 1) {
    resultCardGoal.classList.add('success');
    document.getElementById('resultEmojiGoal').textContent = '🎉';
    document.getElementById('resultTitleGoal').textContent = 'Fantastico!';
  } else if (avgGrade > 10) {
    resultCardGoal.classList.add('error');
    document.getElementById('resultEmojiGoal').textContent = '😅';
    document.getElementById('resultTitleGoal').textContent = 'Difficile...';
  } else if (avgGrade >= 9) {
    resultCardGoal.classList.add('warning');
    document.getElementById('resultEmojiGoal').textContent = '💪';
    document.getElementById('resultTitleGoal').textContent = 'Impegnati!';
  } else if (avgGrade >= 7) {
    resultCardGoal.classList.add('success');
    document.getElementById('resultEmojiGoal').textContent = '👍';
    document.getElementById('resultTitleGoal').textContent = 'Fattibile!';
  } else {
    resultCardGoal.classList.add('success');
    document.getElementById('resultEmojiGoal').textContent = '✅';
    document.getElementById('resultTitleGoal').textContent = 'Ottimo!';
  }

  resultCardGoal.classList.add('show');
  resultCardGoal.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Handle predict form submission
const predictForm = document.getElementById('predictForm');
const resultCardPredict = document.getElementById('resultCardPredict');
const calculateBtnPredict = document.getElementById('calculateBtnPredict');

predictForm.addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const period = periodSelectPredict.value;
  const subject = subjectSelectPredict.value;
  const gradeInputs = document.querySelectorAll('.predict-grade-input');
  const predictedGrades = [];
  
  for (let input of gradeInputs) {
    const value = parseFloat(input.value);
    if (!value || value < 1 || value > 10) {
      showError('Inserisci voti validi (1-10)!');
      return;
    }
    predictedGrades.push(value);
  }

  if (!period || !subject || predictedGrades.length === 0) {
    showError('Compila tutti i campi!');
    return;
  }

  calculateBtnPredict.disabled = true;
  calculateBtnPredict.textContent = 'Calcolo in corso...';

  try {
    const response = await fetch('/predict_average', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        period: period,
        subject: subject,
        predicted_grades: predictedGrades
      })
    });

    const data = await response.json();

    if (response.ok && data.success) {
      displayPredictResult(data);
    } else {
      showError(data.error || 'Errore durante il calcolo');
    }
  } catch (error) {
    showError('Errore di connessione');
  } finally {
    calculateBtnPredict.disabled = false;
    calculateBtnPredict.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
      </svg>
      Prevedi
    `;
  }
});

function displayPredictResult(data) {
  document.getElementById('currentAveragePredict').textContent = data.current_average.toFixed(2);
  document.getElementById('predictedAverage').textContent = data.predicted_average.toFixed(2);
  
  const change = data.predicted_average - data.current_average;
  const changeEl = document.getElementById('averageChange');
  const changeText = change >= 0 ? `+${change.toFixed(2)}` : change.toFixed(2);
  changeEl.textContent = changeText;
  
  // Color the change based on positive/negative
  if (change > 0) {
    changeEl.style.color = 'var(--excellent)';
  } else if (change < 0) {
    changeEl.style.color = 'var(--fail)';
  } else {
    changeEl.style.color = 'var(--text)';
  }
  
  document.getElementById('resultMessagePredict').textContent = data.message;

  // Set result card style
  resultCardPredict.classList.remove('success', 'warning', 'error');
  
  if (change > 0.5) {
    resultCardPredict.classList.add('success');
    document.getElementById('resultEmojiPredict').textContent = '📈';
    document.getElementById('resultTitlePredict').textContent = 'Ottima crescita!';
  } else if (change > 0) {
    resultCardPredict.classList.add('success');
    document.getElementById('resultEmojiPredict').textContent = '✅';
    document.getElementById('resultTitlePredict').textContent = 'In miglioramento!';
  } else if (change === 0) {
    resultCardPredict.classList.add('warning');
    document.getElementById('resultEmojiPredict').textContent = '➡️';
    document.getElementById('resultTitlePredict').textContent = 'Stabile';
  } else if (change > -0.5) {
    resultCardPredict.classList.add('warning');
    document.getElementById('resultEmojiPredict').textContent = '⚠️';
    document.getElementById('resultTitlePredict').textContent = 'Leggero calo';
  } else {
    resultCardPredict.classList.add('error');
    document.getElementById('resultEmojiPredict').textContent = '📉';
    document.getElementById('resultTitlePredict').textContent = 'Attenzione!';
  }

  resultCardPredict.classList.add('show');
  resultCardPredict.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ===== Overall Average Handlers =====

// Add grade input for overall goal calculator
function addOverallGoalGradeInput() {
  numGradesOverallGoal++;
  const container = document.getElementById('overallGoalGradesContainer');
  const gradeGroup = document.createElement('div');
  gradeGroup.className = 'grade-input-group';
  gradeGroup.innerHTML = `
    <span style="font-size: 14px; opacity: 0.8;">${numGradesOverallGoal} ${pluralizeVoto(numGradesOverallGoal)}</span>
    <button type="button" class="remove-grade-btn" onclick="removeOverallGoalGradeInput(this)">×</button>
  `;
  container.appendChild(gradeGroup);
}

function removeOverallGoalGradeInput(btn) {
  if (numGradesOverallGoal > 1) {
    btn.parentElement.remove();
    numGradesOverallGoal--;
    // Update labels
    const groups = document.querySelectorAll('#overallGoalGradesContainer .grade-input-group');
    groups.forEach((group, index) => {
      const span = group.querySelector('span');
      if (span) {
        span.textContent = `${index + 1} ${pluralizeVoto(index + 1)}`;
      }
    });
  }
}

// Add grade input for overall predict calculator
function addOverallPredictGradeInput() {
  numGradesOverallPredict++;
  const container = document.getElementById('overallPredictGradesContainer');
  const gradeGroup = document.createElement('div');
  gradeGroup.className = 'grade-input-group';
  gradeGroup.innerHTML = `
    <input 
      type="number" 
      class="grade-input-small overall-predict-grade-input" 
      min="1" 
      max="10" 
      step="0.5" 
      placeholder="Voto"
      required
    />
    <button type="button" class="remove-grade-btn" onclick="removeOverallPredictGradeInput(this)">×</button>
  `;
  container.appendChild(gradeGroup);
}

function removeOverallPredictGradeInput(btn) {
  if (numGradesOverallPredict > 1) {
    btn.parentElement.remove();
    numGradesOverallPredict--;
  }
}

function updateOverallTargetInput() {
  const targetInput = document.getElementById('targetOverallAverage');
  const targetRangeLabel = document.getElementById('targetOverallRangeLabel');
  const targetHelp = document.getElementById('targetOverallHelp');
  
  const currentOverallAverage = gradesData.all_avr || 0;
  
  targetInput.min = Math.max(1, Math.ceil(currentOverallAverage * 10) / 10);
  targetRangeLabel.textContent = `(${targetInput.min}-10)`;
  targetHelp.textContent = `La tua media generale attuale è ${currentOverallAverage.toFixed(2)}. Imposta un obiettivo superiore.`;
  
  if (targetInput.value && parseFloat(targetInput.value) < targetInput.min) {
    targetInput.value = '';
  }
}

// Initialize on page load
updateOverallTargetInput();

// Handle period selection for Overall Predict
const periodSelectOverallPredict = document.getElementById('periodSelectOverallPredict');
const subjectSelectOverallPredict = document.getElementById('subjectSelectOverallPredict');

periodSelectOverallPredict.addEventListener('change', function() {
  const period = this.value;
  subjectSelectOverallPredict.disabled = false;
  subjectSelectOverallPredict.innerHTML = '<option value="">Seleziona una materia...</option>';
  
  if (period && gradesData[period]) {
    const subjects = Object.keys(gradesData[period]).filter(s => s !== 'period_avr');
    subjects.forEach(subject => {
      const option = document.createElement('option');
      option.value = subject;
      option.textContent = subject;
      subjectSelectOverallPredict.appendChild(option);
    });
  } else {
    subjectSelectOverallPredict.disabled = true;
    subjectSelectOverallPredict.innerHTML = '<option value="">Prima seleziona un periodo...</option>';
  }
});

// Handle overall goal form submission (now only for smart suggestions)
const overallGoalForm = document.getElementById('overallGoalForm');

// Smart suggestion function
async function getSmartSuggestion() {
  const targetAverage = parseFloat(document.getElementById('targetOverallAverage').value);

  if (!targetAverage) {
    showError('Inserisci una media target!');
    return;
  }

  const smartBtn = document.getElementById('smartSuggestBtn');
  smartBtn.disabled = true;
  smartBtn.textContent = 'Calcolo in corso...';

  try {
    const response = await fetch('/calculate_goal_overall', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        target_average: targetAverage,
        num_grades: numGradesOverallGoal
        // No subject - triggers smart suggestions
      })
    });

    const data = await response.json();

    if (response.ok && data.success) {
      displaySmartSuggestions(data);
    } else {
      showError(data.error || 'Errore durante il calcolo');
    }
  } catch (error) {
    showError('Errore di connessione');
  } finally {
    smartBtn.disabled = false;
    smartBtn.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      🎯 Suggerimenti Intelligenti
    `;
  }
}

function displaySmartSuggestions(data) {
  const resultCard = document.getElementById('resultCardSmartSuggestions');
  
  document.getElementById('currentOverallAverageSmart').textContent = data.current_overall_average.toFixed(2);
  document.getElementById('targetOverallAverageSmart').textContent = data.target_average.toFixed(2);
  
  const suggestionsContainer = document.getElementById('suggestionsContainer');
  suggestionsContainer.innerHTML = '';
  
  if (data.suggestions && data.suggestions.length > 0) {
    const header = document.createElement('h3');
    header.style.fontSize = '16px';
    header.style.fontWeight = 'bold';
    header.style.marginBottom = '12px';
    header.style.color = 'var(--text)';
    header.textContent = '📚 Materie Consigliate (ordinate per facilità):';
    suggestionsContainer.appendChild(header);
    
    data.suggestions.forEach((suggestion, index) => {
      const suggestionItem = document.createElement('div');
      suggestionItem.className = 'suggestion-item';
      
      const rank = index + 1;
      const emoji = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '📌';
      
      suggestionItem.innerHTML = `
        <div class="subject-name">${emoji} ${suggestion.subject}</div>
        <div class="suggestion-details">
          <span>Media attuale: ${suggestion.current_average}</span>
          <span class="required-grade">Voto necessario: ${suggestion.required_grade}</span>
        </div>
        <div style="font-size: 12px; margin-top: 4px; opacity: 0.7;">
          ${suggestion.num_current_grades} ${pluralizeCurrentGrades(suggestion.num_current_grades)}
        </div>
      `;
      
      suggestionsContainer.appendChild(suggestionItem);
    });
  } else {
    suggestionsContainer.innerHTML = '<p style="opacity: 0.7;">Nessun suggerimento disponibile.</p>';
  }
  
  document.getElementById('resultMessageSmart').textContent = data.message;
  
  resultCard.classList.add('show');
  resultCard.style.display = 'block';
  resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Handle overall predict form submission
const overallPredictForm = document.getElementById('overallPredictForm');
const resultCardOverallPredict = document.getElementById('resultCardOverallPredict');
const calculateBtnOverallPredict = document.getElementById('calculateBtnOverallPredict');

overallPredictForm.addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const period = periodSelectOverallPredict.value;
  const subject = subjectSelectOverallPredict.value;
  const gradeInputs = document.querySelectorAll('.overall-predict-grade-input');
  const predictedGrades = [];
  
  for (let input of gradeInputs) {
    const value = parseFloat(input.value);
    if (!value || value < 1 || value > 10) {
      showError('Inserisci voti validi (1-10)!');
      return;
    }
    predictedGrades.push(value);
  }

  if (!period || !subject || predictedGrades.length === 0) {
    showError('Compila tutti i campi!');
    return;
  }

  calculateBtnOverallPredict.disabled = true;
  calculateBtnOverallPredict.textContent = 'Calcolo in corso...';

  try {
    const response = await fetch('/predict_average_overall', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        period: period,
        subject: subject,
        predicted_grades: predictedGrades
      })
    });

    const data = await response.json();

    if (response.ok && data.success) {
      displayOverallPredictResult(data);
    } else {
      showError(data.error || 'Errore durante il calcolo');
    }
  } catch (error) {
    showError('Errore di connessione');
  } finally {
    calculateBtnOverallPredict.disabled = false;
    calculateBtnOverallPredict.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
      </svg>
      Prevedi
    `;
  }
});

function displayOverallPredictResult(data) {
  document.getElementById('currentOverallAveragePredict').textContent = data.current_overall_average.toFixed(2);
  document.getElementById('predictedOverallAverage').textContent = data.predicted_overall_average.toFixed(2);
  
  const change = data.predicted_overall_average - data.current_overall_average;
  const changeEl = document.getElementById('overallAverageChange');
  const changeText = change >= 0 ? `+${change.toFixed(2)}` : change.toFixed(2);
  changeEl.textContent = changeText;
  
  // Color the change based on positive/negative
  if (change > 0) {
    changeEl.style.color = 'var(--success)';
  } else if (change < 0) {
    changeEl.style.color = 'var(--primary)';
  } else {
    changeEl.style.color = 'var(--text)';
  }
  
  document.getElementById('resultMessageOverallPredict').textContent = data.message;

  // Set result card style
  resultCardOverallPredict.classList.remove('success', 'warning', 'error');
  
  if (change > 0.5) {
    resultCardOverallPredict.classList.add('success');
    document.getElementById('resultEmojiOverallPredict').textContent = '📈';
    document.getElementById('resultTitleOverallPredict').textContent = 'Ottima crescita!';
  } else if (change > 0) {
    resultCardOverallPredict.classList.add('success');
    document.getElementById('resultEmojiOverallPredict').textContent = '✅';
    document.getElementById('resultTitleOverallPredict').textContent = 'In miglioramento!';
  } else if (change === 0) {
    resultCardOverallPredict.classList.add('warning');
    document.getElementById('resultEmojiOverallPredict').textContent = '➡️';
    document.getElementById('resultTitleOverallPredict').textContent = 'Stabile';
  } else if (change > -0.5) {
    resultCardOverallPredict.classList.add('warning');
    document.getElementById('resultEmojiOverallPredict').textContent = '⚠️';
    document.getElementById('resultTitleOverallPredict').textContent = 'Leggero calo';
  } else {
    resultCardOverallPredict.classList.add('error');
    document.getElementById('resultEmojiOverallPredict').textContent = '📉';
    document.getElementById('resultTitleOverallPredict').textContent = 'Attenzione!';
  }

  resultCardOverallPredict.classList.add('show');
  resultCardOverallPredict.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Handle logout from bottom nav
const logoutNavBtn = document.getElementById('logoutNavBtn');
if (logoutNavBtn) {
  logoutNavBtn.addEventListener('click', () => {
    // Clear client-side credentials
    ClasseVivaAPI.clearCredentials();
    
    // Submit logout form to backend
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/logout';
    document.body.appendChild(form);
    form.submit();
  });
}
