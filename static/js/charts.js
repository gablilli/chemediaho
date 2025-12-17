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

// Get grades data from backend (injected by template)
const gradesData = window.gradesData || [];

// Chart.js configuration
const isDark = root.getAttribute('data-theme') !== 'light';
const textColor = isDark ? '#f1e4e4' : '#1a0a0a';
const gridColor = isDark ? 'rgba(241, 228, 228, 0.1)' : 'rgba(26, 10, 10, 0.1)';

Chart.defaults.color = textColor;
Chart.defaults.borderColor = gridColor;

// Prepare data for all subjects across periods
const periods = Object.keys(gradesData).filter(key => key !== 'all_avr');

// Get all unique subjects
const allSubjects = new Set();
periods.forEach(period => {
  Object.keys(gradesData[period]).forEach(subject => {
    if (subject !== 'period_avr') {
      allSubjects.add(subject);
    }
  });
});

// Generate distinct colors for each subject
const subjectColors = [
  '#4facfe', '#43e97b', '#fa709a', '#fee140',
  '#30cfd0', '#a8edea', '#ff6e7f', '#bfe9ff',
  '#c471ed', '#f64f59', '#12c2e9', '#f093fb',
  '#4facfe', '#00f2fe', '#fa709a', '#ffd200'
];

let subjectChart = null;
let averageChart = null;
let selectedSubjects = Array.from(allSubjects);

// Prepare subject data structure
function prepareSubjectData() {
  const subjectData = {};
  
  allSubjects.forEach(subject => {
    subjectData[subject] = {
      grades: [],
      labels: []
    };
    
    periods.forEach(period => {
      if (gradesData[period][subject]) {
        const grades = gradesData[period][subject].grades;
        grades.forEach((grade, index) => {
          subjectData[subject].grades.push(grade.decimalValue);
          subjectData[subject].labels.push(`P${period}-V${index + 1}`);
        });
      }
    });
  });
  
  return subjectData;
}

// Prepare overall average data by period
function prepareOverallData() {
  const overallData = {
    labels: [],
    values: []
  };
  
  periods.forEach(period => {
    overallData.labels.push(`Periodo ${period}`);
    overallData.values.push(gradesData[period].period_avr);
  });
  
  return overallData;
}

const subjectDataCache = prepareSubjectData();
const overallData = prepareOverallData();

function createSubjectChart(selectedSubjects) {
  const ctx = document.getElementById('subjectChart').getContext('2d');
  
  if (subjectChart) {
    subjectChart.destroy();
  }

  // Prepare datasets for selected subjects only
  const datasets = [];

  // Add selected subjects
  selectedSubjects.forEach((subject, index) => {
    const data = subjectDataCache[subject];
    const colorIndex = Array.from(allSubjects).indexOf(subject) % subjectColors.length;
    
    datasets.push({
      label: subject,
      data: data.grades,
      borderColor: subjectColors[colorIndex],
      backgroundColor: subjectColors[colorIndex] + '20',
      borderWidth: 3,
      fill: false,
      tension: 0.4,
      pointRadius: 5,
      pointHoverRadius: 7,
      pointBackgroundColor: subjectColors[colorIndex],
      pointBorderColor: '#fff',
      pointBorderWidth: 2
    });
  });

  // Collect all labels
  let allLabels = [];
  selectedSubjects.forEach(subject => {
    allLabels = allLabels.concat(subjectDataCache[subject].labels);
  });
  
  // Use unique labels, preserving order
  const uniqueLabels = [...new Set(allLabels)];
  
  // Prepare data arrays matching labels
  const finalDatasets = datasets.map((dataset, idx) => {
    const subject = selectedSubjects[idx];
    const subjectLabels = subjectDataCache[subject].labels;
    const subjectGrades = subjectDataCache[subject].grades;
    
    const mappedData = uniqueLabels.map(label => {
      const labelIdx = subjectLabels.indexOf(label);
      return labelIdx >= 0 ? subjectGrades[labelIdx] : null;
    });
    
    return { ...dataset, data: mappedData };
  });
  
  subjectChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: uniqueLabels,
      datasets: finalDatasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: {
            boxWidth: 20,
            padding: 15,
            usePointStyle: true
          }
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          padding: 12,
          displayColors: true,
          callbacks: {
            label: function(context) {
              let label = context.dataset.label || '';
              if (label) {
                label += ': ';
              }
              if (context.parsed.y !== null) {
                label += context.parsed.y.toFixed(2);
              }
              return label;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: false,
          min: 4,
          max: 10,
          ticks: {
            stepSize: 1
          },
          grid: {
            color: gridColor
          }
        },
        x: {
          grid: {
            display: false
          },
          ticks: {
            maxRotation: 45,
            minRotation: 45
          }
        }
      }
    }
  });
}

function createAverageChart() {
  const ctx = document.getElementById('averageChart').getContext('2d');
  
  if (averageChart) {
    averageChart.destroy();
  }

  averageChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: overallData.labels,
      datasets: [{
        label: 'Media Generale',
        data: overallData.values,
        borderColor: 'rgba(240, 51, 51, 0.8)',
        backgroundColor: 'rgba(240, 51, 51, 0.2)',
        borderWidth: 3,
        fill: true,
        tension: 0.4,
        pointRadius: 6,
        pointHoverRadius: 8,
        pointBackgroundColor: 'rgba(240, 51, 51, 0.8)',
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: {
            boxWidth: 20,
            padding: 15,
            usePointStyle: true
          }
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          padding: 12,
          displayColors: true,
          callbacks: {
            label: function(context) {
              let label = context.dataset.label || '';
              if (label) {
                label += ': ';
              }
              if (context.parsed.y !== null) {
                label += context.parsed.y.toFixed(2);
              }
              return label;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: false,
          min: 4,
          max: 10,
          ticks: {
            stepSize: 1
          },
          grid: {
            color: gridColor
          }
        },
        x: {
          grid: {
            display: false
          }
        }
      }
    }
  });
}

// Create subject selector buttons
function createSubjectButtons() {
  const selector = document.getElementById('subjectSelector');
  
  // Add "All" button
  const allBtn = document.createElement('button');
  allBtn.className = 'subject-btn active';
  allBtn.textContent = 'Tutte';
  allBtn.onclick = () => {
    document.querySelectorAll('.subject-btn').forEach(b => b.classList.remove('active'));
    allBtn.classList.add('active');
    selectedSubjects = Array.from(allSubjects);
    createSubjectChart(selectedSubjects);
  };
  selector.appendChild(allBtn);
  
  // Add individual subject buttons
  allSubjects.forEach(subject => {
    const btn = document.createElement('button');
    btn.className = 'subject-btn';
    btn.textContent = subject;
    btn.onclick = () => {
      const isActive = btn.classList.contains('active');
      
      // If clicking on "All", deselect it
      if (allBtn.classList.contains('active')) {
        allBtn.classList.remove('active');
        selectedSubjects = [];
      }
      
      // Toggle this button
      if (isActive) {
        btn.classList.remove('active');
        selectedSubjects = selectedSubjects.filter(s => s !== subject);
      } else {
        btn.classList.add('active');
        selectedSubjects.push(subject);
      }
      
      // If no subjects selected, select all
      if (selectedSubjects.length === 0) {
        allBtn.classList.add('active');
        selectedSubjects = Array.from(allSubjects);
      }
      
      // If all subjects selected, activate "All" button
      if (selectedSubjects.length === allSubjects.size) {
        allBtn.classList.add('active');
        document.querySelectorAll('.subject-btn').forEach(b => {
          if (b !== allBtn) b.classList.remove('active');
        });
      }
      
      createSubjectChart(selectedSubjects);
    };
    selector.appendChild(btn);
  });
}

// Initialize charts
createSubjectButtons();
createSubjectChart(selectedSubjects);
createAverageChart();

// Update charts when theme changes - without re-animation
themeToggle.addEventListener('click', () => {
  // Wait for theme to be applied
  setTimeout(() => {
    const isDark = !root.getAttribute('data-theme') || root.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#f1e4e4' : '#1a0a0a';
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    
    // Update subject chart colors without animation
    if (subjectChart) {
      subjectChart.options.scales.y.ticks.color = textColor;
      subjectChart.options.scales.x.ticks.color = textColor;
      subjectChart.options.scales.y.grid.color = gridColor;
      subjectChart.options.scales.x.grid.color = gridColor;
      subjectChart.options.plugins.legend.labels.color = textColor;
      subjectChart.options.animation = false; // Disable animation for update
      subjectChart.update('none'); // Update without animation
      subjectChart.options.animation = { duration: 750, easing: 'easeInOutQuart' }; // Re-enable for future updates
    }
    
    // Update average chart colors without animation
    if (averageChart) {
      averageChart.options.scales.y.ticks.color = textColor;
      averageChart.options.scales.x.ticks.color = textColor;
      averageChart.options.scales.y.grid.color = gridColor;
      averageChart.options.scales.x.grid.color = gridColor;
      averageChart.options.animation = false;
      averageChart.update('none');
      averageChart.options.animation = { duration: 750, easing: 'easeInOutQuart' };
    }
  }, 50);
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
