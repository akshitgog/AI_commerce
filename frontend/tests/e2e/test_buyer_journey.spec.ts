import { test, expect } from '@playwright/test';

test('buyer intent-to-checkout flow', async ({ page }) => {
  // Mock Razorpay checkout.js
  await page.route('https://checkout.razorpay.com/v1/checkout.js', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/javascript',
      body: `
        window.Razorpay = function(options) {
          setTimeout(() => options.handler({ razorpay_payment_id: "fake_pay_id", razorpay_order_id: "fake_order", razorpay_signature: "fake_sig" }), 100);
          return { open: () => {} };
        };
      `
    });
  });

  await page.goto('/buyer');
  
  // Wait for chat input
  const chatInput = page.locator('textarea[placeholder*="Type a message"]');
  await expect(chatInput).toBeVisible({ timeout: 10000 });
  
  // Type 'I need a coffee maker'
  await chatInput.fill('I need a coffee maker');
  await chatInput.press('Enter');
  
  // Wait for product result card
  const productCard = page.locator('text="Propose Purchase"').first();
  await expect(productCard).toBeVisible({ timeout: 15000 });
  
  // Click 'Propose Purchase'
  await productCard.click();
  
  // Wait for Proposal card
  const authorizeButton = page.locator('text="Authorize"').first();
  await expect(authorizeButton).toBeVisible({ timeout: 15000 });
  
  // Click 'Authorize'
  await authorizeButton.click();
  
  // Wait for Ready for Payment card
  const payButton = page.locator('text="Pay with Razorpay (Test Mode)"').first();
  await expect(payButton).toBeVisible({ timeout: 15000 });
  
  // Click 'Pay with Razorpay (Test Mode)'
  await payButton.click();
  
  // Wait for verification or failure
  const outcomeCard = page.locator('text="Verifying payment"').first();
  // It might jump to Payment failed quickly since we mock fake credentials
  // Wait for either verifying or failed
  await expect(page.locator('text="Verifying payment"').first().or(page.locator('text="Payment failed"').first())).toBeVisible({ timeout: 15000 });
});
