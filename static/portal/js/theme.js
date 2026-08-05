// Theme toggle logic (Light / Dark mode)
(function () {
  const STORAGE_KEY = 'portal-theme';

  function getPreferredTheme() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return saved;
    return 'dark'; // Default theme is dark (deep blue)
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
    
    // Update theme toggle icons if present
    const sunIcon = document.getElementById('theme-toggle-sun');
    const moonIcon = document.getElementById('theme-toggle-moon');
    if (sunIcon && moonIcon) {
      if (theme === 'dark') {
        sunIcon.classList.remove('hidden');
        moonIcon.classList.add('hidden');
      } else {
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
      }
    }

    // Trigger custom event so charts can refresh
    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
  }

  // Apply initially before render
  applyTheme(getPreferredTheme());

  document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('theme-toggle-btn');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme') || 'dark';
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next);
      });
    }
  });

  window.PortalTheme = {
    get: () => document.documentElement.getAttribute('data-theme') || 'dark',
    set: applyTheme
  };
})();
