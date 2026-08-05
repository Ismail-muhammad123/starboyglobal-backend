// AJAX Forms, Inline Editing, Modals and Toast Notifications
(function () {
  // CSRF Token Helper
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // Toast Notification System
  function showToast(message, type = 'info', title = '') {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `pointer-events-auto p-4 rounded-lg shadow-lg border text-sm flex items-start gap-3 transition-all duration-300 transform translate-y-4 opacity-0`;
    
    let bgBorder = 'bg-slate-800 border-slate-700 text-white';
    if (type === 'success') bgBorder = 'bg-emerald-950 border-emerald-800 text-emerald-100';
    if (type === 'error') bgBorder = 'bg-red-950 border-red-800 text-red-100';
    if (type === 'warning') bgBorder = 'bg-amber-950 border-amber-800 text-amber-100';

    toast.className += ` ${bgBorder}`;
    toast.innerHTML = `
      <div class="flex-1">
        ${title ? `<div class="font-semibold mb-0.5">${title}</div>` : ''}
        <div>${message}</div>
      </div>
      <button onclick="this.parentElement.remove()" class="text-slate-400 hover:text-white">&times;</button>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.remove('translate-y-4', 'opacity-0');
    }, 10);

    setTimeout(() => {
      toast.classList.add('opacity-0', 'translate-y-4');
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // Modal helpers
  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('hidden');
      modal.classList.add('flex');
    }
  }

  function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('hidden');
      modal.classList.remove('flex');
    }
  }

  // AJAX Form Handler
  function initAjaxForms() {
    document.querySelectorAll('form[data-ajax="true"]').forEach((form) => {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn ? submitBtn.innerHTML : '';
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerHTML = '<span class="inline-block animate-spin mr-2">🌀</span> Processing...';
        }

        try {
          const url = form.action;
          const method = (form.method || 'POST').toUpperCase();
          const formData = new FormData(form);

          const response = await fetch(url, {
            method: method,
            headers: {
              'X-CSRFToken': getCookie('csrftoken'),
              'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
          });

          const resData = await response.json();
          if (response.ok && resData.status !== 'error') {
            showToast(resData.message || 'Operation completed successfully.', 'success');
            if (form.getAttribute('data-reload') === 'true') {
              setTimeout(() => window.location.reload(), 800);
            }
            if (form.getAttribute('data-close-modal')) {
              closeModal(form.getAttribute('data-close-modal'));
            }
          } else {
            showToast(resData.message || resData.error || 'Request failed.', 'error');
          }
        } catch (err) {
          showToast('An unexpected error occurred.', 'error');
        } finally {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
          }
        }
      });
    });
  }

  // Inline Cell Price Editor
  function initInlineCellEdit() {
    document.querySelectorAll('.inline-edit-cell').forEach((cell) => {
      cell.addEventListener('click', function () {
        if (this.dataset.editing === 'true') return;
        this.dataset.editing = 'true';

        const currentValue = this.dataset.value || this.innerText.trim().replace(/[^0-9.]/g, '');
        const fieldName = this.dataset.field;
        const endpoint = this.dataset.endpoint;

        const input = document.createElement('input');
        input.type = 'number';
        input.step = '0.01';
        input.value = currentValue;
        input.className = 'w-24 px-2 py-1 bg-slate-900 border border-blue-500 text-white rounded text-xs focus:outline-none';

        const originalHTML = this.innerHTML;
        this.innerHTML = '';
        this.appendChild(input);
        input.focus();

        const saveChange = async () => {
          const newValue = input.value.trim();
          if (newValue === currentValue || newValue === '') {
            cell.innerHTML = originalHTML;
            cell.dataset.editing = 'false';
            return;
          }

          try {
            const body = {};
            body[fieldName] = newValue;
            const res = await fetch(endpoint, {
              method: 'PATCH',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
              },
              body: JSON.stringify(body)
            });
            const data = await res.json();
            if (res.ok) {
              cell.dataset.value = newValue;
              cell.innerHTML = `₦${parseFloat(newValue).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
              showToast('Price updated.', 'success');
            } else {
              showToast(data.error || 'Failed to update price.', 'error');
              cell.innerHTML = originalHTML;
            }
          } catch (e) {
            showToast('Failed to save edit.', 'error');
            cell.innerHTML = originalHTML;
          } finally {
            cell.dataset.editing = 'false';
          }
        };

        input.addEventListener('blur', saveChange);
        input.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            input.blur();
          }
          if (e.key === 'Escape') {
            cell.innerHTML = originalHTML;
            cell.dataset.editing = 'false';
          }
        });
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    initAjaxForms();
    initInlineCellEdit();
  });

  window.PortalForms = {
    toast: showToast,
    openModal: openModal,
    closeModal: closeModal,
    getCookie: getCookie
  };
})();
