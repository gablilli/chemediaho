import { initTheme, initLogout, initRefresh } from './common';

// Modal functions
function showModal(grade: any): void {
  const modal = document.getElementById('gradeModal');
  if (!modal) return;

  // Populate modal with grade data
  const modalGrade = document.getElementById('modalGrade');
  const modalDate = document.getElementById('modalDate');
  const modalComponent = document.getElementById('modalComponent');
  const modalTeacher = document.getElementById('modalTeacher');
  const modalNotes = document.getElementById('modalNotes');

  if (modalGrade) modalGrade.textContent = grade.decimalValue || grade.displayValue || '-';
  if (modalDate) modalDate.textContent = grade.evtDate || '-';
  if (modalComponent) modalComponent.textContent = grade.componentDesc || '-';
  if (modalTeacher) modalTeacher.textContent = grade.teacherName || '-';
  if (modalNotes) modalNotes.textContent = grade.notesForFamily || 'Nessuna nota';

  modal.style.display = 'flex';
}

function closeModal(): void {
  const modal = document.getElementById('gradeModal');
  if (modal) {
    modal.style.display = 'none';
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initLogout();
  initRefresh();
  
  // Close modal when clicking outside
  const modal = document.getElementById('gradeModal');
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeModal();
      }
    });
  }
});

// Export functions for use in HTML onclick attributes
(window as any).showModal = showModal;
(window as any).closeModal = closeModal;
