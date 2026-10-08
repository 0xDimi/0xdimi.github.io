const filters = Array.from(document.querySelectorAll('[data-filter]'));
const cards = Array.from(document.querySelectorAll('#work-grid .work-card'));

function setFilter(kind) {
  const requested = kind === 'perspectives' ? 'strategies' : kind;
  const selected = filters.some((button) => button.dataset.filter === requested) ? requested : 'all';
  for (const button of filters) {
    const active = button.dataset.filter === selected;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  }
  for (const card of cards) card.hidden = selected !== 'all' && card.dataset.kind !== selected;
  if (selected === 'all') history.replaceState(null, '', location.pathname + location.search + '#library');
  else history.replaceState(null, '', location.pathname + location.search + '#library-' + selected);
}

filters.forEach((button) => button.addEventListener('click', () => setFilter(button.dataset.filter)));
document.querySelectorAll('[data-jump-filter]').forEach((link) => {
  link.addEventListener('click', (event) => {
    event.preventDefault();
    setFilter(link.dataset.jumpFilter);
    document.getElementById('library').scrollIntoView();
  });
});

const initialFilter = location.hash.startsWith('#library-') ? location.hash.slice('#library-'.length) : 'all';
if (initialFilter !== 'all') {
  setFilter(initialFilter);
  document.getElementById('library').scrollIntoView();
}

window.addEventListener('hashchange', () => {
  if (location.hash === '#library' || location.hash.startsWith('#library-')) {
    setFilter(location.hash.startsWith('#library-') ? location.hash.slice('#library-'.length) : 'all');
  }
});
