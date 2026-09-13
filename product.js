const notice = document.querySelector('.catalog-notice');
const bagButtons = document.querySelectorAll('.add-button');
let noticeTimer;

bagButtons.forEach((button) => {
  button.addEventListener('click', () => {
    button.classList.add('is-added');
    button.textContent = 'Added';
    notice.textContent = `${button.dataset.product} added to your bag`;
    notice.classList.add('is-visible');
    window.clearTimeout(noticeTimer);
    noticeTimer = window.setTimeout(() => notice.classList.remove('is-visible'), 2400);
  });
});
