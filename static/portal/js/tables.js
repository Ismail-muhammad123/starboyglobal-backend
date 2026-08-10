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

  window.updateBulkActionBar = function(tableId) {
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
  };
});

window.executeBulkAction = async function(tableId, itemType, action) {
  const table = document.getElementById(tableId);
  if (!table) return;

  const checked = table.querySelectorAll('tbody input[type="checkbox"]:checked');
  const selectedIds = Array.from(checked).map((cb) => cb.value);

  if (selectedIds.length === 0) {
    if (window.PortalUtils && window.PortalUtils.showToast) {
      window.PortalUtils.showToast('Please select at least one item.', 'warning');
    } else {
      alert('Please select at least one item.');
    }
    return;
  }

  const actionLabels = {
    'delete': 'PERMANENTLY DELETE',
    'deactivate': 'DEACTIVATE',
    'activate': 'ACTIVATE'
  };
  const label = actionLabels[action] || action.toUpperCase();

  if (!confirm(`Are you sure you want to ${label} ${selectedIds.length} selected item(s)?`)) {
    return;
  }

  try {
    const csrfToken = (window.PortalForms && window.PortalForms.getCookie)
      ? window.PortalForms.getCookie('csrftoken')
      : (document.cookie.split('; ').find((r) => r.startsWith('csrftoken='))?.split('=')[1] || '');

    const response = await fetch('/portal/services/bulk-action/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({
        item_type: itemType,
        action: action,
        ids: selectedIds
      })
    });

    const data = await response.json();
    if (data.status === 'success') {
      if (window.PortalUtils && window.PortalUtils.showToast) {
        window.PortalUtils.showToast(data.message, 'success');
      } else {
        alert(data.message);
      }
      setTimeout(() => window.location.reload(), 600);
    } else {
      if (window.PortalUtils && window.PortalUtils.showToast) {
        window.PortalUtils.showToast(data.message || 'Bulk action failed.', 'error');
      } else {
        alert(data.message || 'Bulk action failed.');
      }
    }
  } catch (err) {
    console.error('Bulk action error:', err);
    if (window.PortalUtils && window.PortalUtils.showToast) {
      window.PortalUtils.showToast('Server error executing bulk action.', 'error');
    }
  }
};

