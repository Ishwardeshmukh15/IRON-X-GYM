const menuToggle = document.querySelector('.menu-toggle');
const siteNav = document.querySelector('.site-nav');

menuToggle.addEventListener('click', () => {
  const isOpen = siteNav.classList.toggle('is-open');
  menuToggle.setAttribute('aria-expanded', String(isOpen));
});

document.querySelectorAll('.site-nav a').forEach((link) => {
  link.addEventListener('click', () => {
    siteNav.classList.remove('is-open');
    menuToggle.setAttribute('aria-expanded', 'false');
  });
});

const memberStories = [
  ['“I came for the workouts. I stayed because this is the first gym that feels like my people.”', '— Nia, member since 2021'],
  ['“IronX gave me the confidence to take up space, in the gym and everywhere else.”', '— Jordan, member since 2022'],
  ['“Every session is hard. Every session is worth it. That is the whole point.”', '— Alex, member since 2019'],
];

const quote = document.querySelector('#member-quote');
const name = document.querySelector('#member-name');
document.querySelectorAll('[data-quote]').forEach((button) => {
  button.addEventListener('click', () => {
    const story = memberStories[Number(button.dataset.quote)];
    quote.textContent = story[0];
    name.textContent = story[1];
    document.querySelectorAll('[data-quote]').forEach((dot) => dot.classList.remove('is-active'));
    button.classList.add('is-active');
  });
});

