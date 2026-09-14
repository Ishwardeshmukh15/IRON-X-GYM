const notice = document.querySelector('.catalog-notice');
const bagButtons = document.querySelectorAll('.add-button');
let noticeTimer;

function readCart() {
  try { return JSON.parse(localStorage.getItem('ironx_cart') || '[]'); } catch { return []; }
}

function writeCart(cart) {
  localStorage.setItem('ironx_cart', JSON.stringify(cart));
}

bagButtons.forEach((button) => {
  button.addEventListener('click', async () => {
    const category = window.location.pathname.includes('nutrition') ? 'nutrition' : 'store';
    const card = button.closest('.product-card');
    const price = Number((card.querySelector('.product-price')?.textContent || '0').replace(/[^0-9.]/g, ''));
    const cart = readCart();
    const existing = cart.find((item) => item.product === button.dataset.product);
    if (existing) existing.quantity += 1;
    else cart.push({ product: button.dataset.product, category, price, quantity: 1 });
    writeCart(cart);
    button.classList.add('is-added');
    button.textContent = 'Added';
    notice.textContent = `${button.dataset.product} added to your bag / cart`;
    notice.classList.add('is-visible');
    window.clearTimeout(noticeTimer);
    noticeTimer = window.setTimeout(() => notice.classList.remove('is-visible'), 2400);

    try {
      const response = await fetch('/api/me');
      const account = await response.json();
      if (account.user) {
        window.setTimeout(() => { window.location.href = 'dashboard.html'; }, 350);
      }
    } catch {
      // Keep the product page usable if the session check is unavailable.
    }
  });
});
