// Tables sorting, filtering and selection helper
document.addEventListener('DOMContentLoaded', () => {
  // Table search filter (for client side filtered tables)
  document.querySelectorAll('input[data-table-search]').forEach((input) => {
    const tableId = input.getAttribute('data-table-search');
    const table = document.getElementById(tableId);
    if (!table) return;

    input.addEventListener('input', () => {
      const term = input.value.toLowerCase().trim();
      const rows = table.querySelectorAll('tbody tr');

      rows.forEach((row) => {
        const text = row.innerText.toLowerCase();
        if (text.includes(term)) {
          row.style.display = '';
        } else {
          row.style.display = 'none';
        }
      });
    });
  });

  // Table Select All checkboxes
  document.querySelectorAll('input[data-select-all]').forEach((selectAll) => {
    const tableId = selectAll.getAttribute('data-select-all');
    const table = document.getElementById(tableId);
    if (!table) return;

    selectAll.addEventListener('change', () => {
      const checkboxes = table.querySelectorAll('tbody input[type="checkbox"]');
      checkboxes.forEach((cb) => {
        cb.checked = selectAll.checked;
      });
      updateBulkActionBar(tableId);
    });

    table.querySelectorAll('tbody input[type="checkbox"]').forEach((cb) => {
      cb.addEventListener('change', () => updateBulkActionBar(tableId));
    });
  });

  function updateBulkActionBar(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;
    const checked = table.querySelectorAll('tbody input[type="checkbox"]:checked');
    const bulkBar = document.getElementById(`${tableId}-bulk-actions`);
    const countDisplay = document.getElementById(`${tableId}-selected-count`);

    if (bulkBar) {
      if (checked.length > 0) {
        bulkBar.classList.remove('hidden');
        if (countDisplay) countDisplay.innerText = `${checked.length} selected`;
      } else {
        bulkBar.classList.add('hidden');
      }
    }
  }
});
