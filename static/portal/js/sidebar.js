// Sidebar Accordion and Mobile Overlay Logic
document.addEventListener('DOMContentLoaded', () => {
  const currentPath = window.location.pathname;
  const groups = document.querySelectorAll('.sidebar-group');
  let activeGroupFound = false;

  // 1. Initial State: Find group containing active link
  groups.forEach((group) => {
    const links = group.querySelectorAll('a[href]');
    let matches = false;

    links.forEach((link) => {
      const href = link.getAttribute('href');
      if (href && href !== '#' && (currentPath === href || (href !== '/portal/' && currentPath.startsWith(href)))) {
        matches = true;
        link.classList.add('bg-blue-600/20', 'text-blue-400', 'font-semibold');
      }
    });

    if (matches && !activeGroupFound) {
      group.classList.add('open');
      activeGroupFound = true;
    } else {
      group.classList.remove('open');
    }
  });

  // If no group was active, restore from sessionStorage if available
  if (!activeGroupFound) {
    const savedGroupId = sessionStorage.getItem('portal-active-group');
    if (savedGroupId) {
      const savedGroup = document.getElementById(savedGroupId);
      if (savedGroup) savedGroup.classList.add('open');
    }
  }

  // 2. Accordion Click Handlers
  groups.forEach((group) => {
    const header = group.querySelector('.sidebar-group-header');
    if (header) {
      header.addEventListener('click', (e) => {
        e.preventDefault();
        const isOpen = group.classList.contains('open');

        // Close all other groups (Accordion style)
        groups.forEach((other) => {
          if (other !== group) {
            other.classList.remove('open');
          }
        });

        // Toggle target group
        if (isOpen) {
          group.classList.remove('open');
          sessionStorage.removeItem('portal-active-group');
        } else {
          group.classList.add('open');
          if (group.id) {
            sessionStorage.setItem('portal-active-group', group.id);
          }
        }
      });
    }
  });

  // 3. Mobile Sidebar Toggle & Backdrop
  const mobileToggle = document.getElementById('mobile-sidebar-toggle');
  const sidebar = document.getElementById('portal-sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');

  function openSidebar() {
    if (sidebar) sidebar.classList.remove('-translate-x-full');
    if (backdrop) backdrop.classList.remove('hidden');
  }

  function closeSidebar() {
    if (sidebar) sidebar.classList.add('-translate-x-full');
    if (backdrop) backdrop.classList.add('hidden');
  }

  if (mobileToggle) {
    mobileToggle.addEventListener('click', () => {
      const isHidden = sidebar && sidebar.classList.contains('-translate-x-full');
      if (isHidden) openSidebar(); else closeSidebar();
    });
  }

  if (backdrop) {
    backdrop.addEventListener('click', closeSidebar);
  }
});
