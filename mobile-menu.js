document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('nav[aria-label="Navegação principal"], nav[aria-label="Main navigation"]').forEach(function (nav) {
    if (nav.querySelector('.mobile-menu-toggle')) return;

    const lang = nav.querySelector('.lang-switch');
    const links = Array.from(nav.querySelectorAll('a:not(.lang-switch)'));
    if (!links.length) return;

    const menu = document.createElement('div');
    menu.className = 'mobile-nav-menu';
    links.forEach(function (link) { menu.appendChild(link); });

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'mobile-menu-toggle';
    button.setAttribute('aria-label', 'Abrir menu');
    button.setAttribute('aria-expanded', 'false');
    button.innerHTML = '<span></span><span></span><span></span>';

    nav.insertBefore(button, nav.firstChild);
    nav.insertBefore(menu, lang || null);

    button.addEventListener('click', function () {
      const open = nav.classList.toggle('menu-open');
      button.setAttribute('aria-expanded', String(open));
      button.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
    });

    menu.addEventListener('click', function (event) {
      if (event.target.closest('a')) {
        nav.classList.remove('menu-open');
        button.setAttribute('aria-expanded', 'false');
        button.setAttribute('aria-label', 'Abrir menu');
      }
    });
  });
});
