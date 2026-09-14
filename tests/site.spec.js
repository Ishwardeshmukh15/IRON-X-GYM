const { test, expect } = require('@playwright/test');

const pages = [
  ['homepage', '/index.html'],
  ['booking', '/booking.html'],
  ['coaches', '/coaches.html'],
  ['membership', '/membership.html'],
  ['nutrition', '/nutrition.html'],
  ['store', '/store.html'],
];

test.describe('IronX Gym pages', () => {
  for (const [name, path] of pages) {
    test(`${name} loads successfully`, async ({ page }) => {
      const consoleErrors = [];
      page.on('console', (message) => {
        if (message.type() === 'error') consoleErrors.push(message.text());
      });
      page.on('pageerror', (error) => consoleErrors.push(error.message));

      const response = await page.goto(path);
      expect(response.status()).toBe(200);
      await expect(page.locator('body')).toBeVisible();
      await expect(page.locator('h1')).toBeVisible();
      expect(consoleErrors).toEqual([]);
    });
  }
});

test('homepage navigation and mobile menu work', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/index.html');
  await page.locator('.menu-toggle').click();
  await expect(page.locator('.site-nav')).toHaveClass(/is-open/);
  await expect(page.locator('.menu-toggle')).toHaveAttribute('aria-expanded', 'true');
  await page.locator('.site-nav a[href="membership.html"]').click();
  await expect(page).toHaveURL(/membership\.html$/);
});

test('store add-to-bag feedback works', async ({ page }) => {
  await page.goto('/store.html');
  const button = page.locator('.add-button').first();
  await button.click();
  await expect(button).toHaveText('Added');
  await expect(page.locator('.catalog-notice')).toContainText('added to your bag');
});

test('booking form validates and submits the expected payload', async ({ page }) => {
  await page.goto('/booking.html');
  await page.locator('button[type="submit"]').click();
  await expect(page.locator('input:invalid, select:invalid')).toHaveCount(8);

  let requestBody;
  await page.route('**/api/booking', async (route) => {
    requestBody = JSON.parse(route.request().postData());
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ message: 'Thanks. The IronX team will be in touch soon.' }),
    });
  });

  await page.locator('#booking-name').fill('Alex Morgan');
  await page.locator('#booking-age').fill('25');
  await page.locator('#booking-location').fill('Mumbai');
  await page.locator('#booking-email').fill('alex@example.com');
  await page.locator('#booking-phone').fill('+91 5550000000');
  await page.locator('#booking-height').fill('175');
  await page.locator('#booking-weight').fill('75');
  await page.locator('#booking-body-type').selectOption({ label: 'Athletic' });
  await page.locator('button[type="submit"]').click();

  await expect(page.locator('.booking-success')).toHaveText('Thanks. The IronX team will be in touch soon.');
  expect(requestBody).toMatchObject({ name: 'Alex Morgan', email: 'alex@example.com', body_type: 'Athletic' });
});
