function isTypingElement(el) {
  if (!el) return false;
  const tag = el.tagName;
  return (
    ['INPUT', 'TEXTAREA', 'SELECT'].includes(tag) ||
    el.isContentEditable
  );
}

document.addEventListener('keydown', function (e) {
  const key = e.key.toLowerCase();
  const isCtrl = e.ctrlKey || e.metaKey;
  const isShift = e.shiftKey;
  const isAlt = e.altKey;
  const typing = isTypingElement(e.target);

  const go = (path) => {
    window.location.href = path;
  };

  // Ctrl+F — фокус на поиск
  if (isCtrl && !isShift && !isAlt && key === 'f') {
    const searchInput = document.querySelector('input[name="q"]');
    if (searchInput) {
      searchInput.focus();
      if (searchInput.select) {
        searchInput.select();
      }
      e.preventDefault();
    }
    return;
  }

  // не мешаем вводу текста, если нет модификаторов
  if (!isCtrl && !isAlt && !isShift && typing) {
    return;
  }

  // Ctrl+N — создать товар (ADMIN/MANAGER)
  if (isCtrl && !isShift && !isAlt && key === 'n') {
    const role = document.body?.dataset?.userRole || window.CURRENT_USER_ROLE;
    if (role === 'ADMIN' || role === 'MANAGER') {
      go('/admin/catalog/product/add/');
      e.preventDefault();
    }
    return;
  }

  // Ctrl+Shift+O — корзина
  if (isCtrl && isShift && !isAlt && key === 'o') {
    go('/cart/');
    e.preventDefault();
    return;
  }

  // Alt+1..4 — быстрые разделы
  if (isAlt && !isCtrl && !isShift) {
    if (key === '1') {
      go('/');
      e.preventDefault();
    }
    if (key === '2') {
      go('/cart/');
      e.preventDefault();
    }
    if (key === '3') {
      go('/profile/');
      e.preventDefault();
    }
    if (key === '4') {
      go('/settings/');
      e.preventDefault();
    }
    return;
  }

  // Ctrl+L — страница логина
  if (isCtrl && !isShift && !isAlt && key === 'l') {
    go('/login/');
    e.preventDefault();
  }
});
