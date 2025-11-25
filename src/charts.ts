import { initTheme, initLogout, initRefresh } from './common';

// Main chart initialization function
function initCharts(gradesData: any): void {
  const root = document.documentElement;
  const isDark = root.getAttribute('data-theme') !== 'light';
  const textColor = isDark ? '#f1e4e4' : '#1a0a0a';
  const gridColor = isDark ? 'rgba(241, 228, 228, 0.1)' : 'rgba(26, 10, 10, 0.1)';

  // Check if Chart.js is loaded
  if (typeof (window as any).Chart === 'undefined') {
    console.error('Chart.js not loaded');
    return;
  }

  const Chart = (window as any).Chart;
  Chart.defaults.color = textColor;
  Chart.defaults.borderColor = gridColor;

  // Prepare data for all subjects across periods
  const periods = Object.keys(gradesData).filter(key => key !== 'all_avr');
  
  // Get all unique subjects
  const allSubjects = new Set<string>();
  periods.forEach(period => {
    Object.keys(gradesData[period]).forEach(subject => {
      if (subject !== 'period_avr') {
        allSubjects.add(subject);
      }
    });
  });

  // Prepare datasets for line chart
  const datasets: any[] = [];
  const subjectColors: { [key: string]: string } = {};
  const colorPalette = [
    '#f03333', '#4caf50', '#4facfe', '#ffa500',
    '#9c27b0', '#00bcd4', '#ff5722', '#8bc34a'
  ];

  let colorIndex = 0;
  allSubjects.forEach(subject => {
    subjectColors[subject] = colorPalette[colorIndex % colorPalette.length];
    colorIndex++;

    const data = periods.map(period => {
      const value = gradesData[period][subject];
      return typeof value === 'number' ? value : null;
    });

    datasets.push({
      label: subject,
      data: data,
      borderColor: subjectColors[subject],
      backgroundColor: subjectColors[subject] + '33',
      tension: 0.4,
      spanGaps: true
    });
  });

  // Create line chart
  const lineChartCanvas = document.getElementById('lineChart') as HTMLCanvasElement;
  if (lineChartCanvas) {
    const lineCtx = lineChartCanvas.getContext('2d');
    if (lineCtx) {
      new Chart(lineCtx, {
        type: 'line',
        data: {
          labels: periods,
          datasets: datasets
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                boxWidth: 12,
                padding: 10,
                font: { size: 11 }
              }
            },
            title: {
              display: true,
              text: 'Andamento Voti per Materia',
              font: { size: 16, weight: 'bold' }
            }
          },
          scales: {
            y: {
              beginAtZero: false,
              min: 0,
              max: 10,
              ticks: { stepSize: 1 }
            }
          }
        }
      });
    }
  }

  // Create bar chart for period averages
  const periodAverages = periods.map(period => gradesData[period].period_avr || 0);
  const barChartCanvas = document.getElementById('barChart') as HTMLCanvasElement;
  if (barChartCanvas) {
    const barCtx = barChartCanvas.getContext('2d');
    if (barCtx) {
      new Chart(barCtx, {
        type: 'bar',
        data: {
          labels: periods,
          datasets: [{
            label: 'Media Periodo',
            data: periodAverages,
            backgroundColor: '#f03333',
            borderColor: '#c83737',
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            title: {
              display: true,
              text: 'Media per Periodo',
              font: { size: 16, weight: 'bold' }
            }
          },
          scales: {
            y: {
              beginAtZero: false,
              min: 0,
              max: 10,
              ticks: { stepSize: 1 }
            }
          }
        }
      });
    }
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initLogout();
  initRefresh();
  
  // Get grades data from window object (injected by backend)
  const gradesData = (window as any).gradesData;
  if (gradesData) {
    initCharts(gradesData);
  }
});
