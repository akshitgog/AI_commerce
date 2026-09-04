import { test, expect } from '@playwright/test';

async function submitBuyerSearch(page: import('@playwright/test').Page) {
  const chatInput = page.getByPlaceholder('Ask about products…');
  await expect(chatInput).toBeEnabled();
  await chatInput.fill('I need a coffee maker');
  await chatInput.press('Enter');
  const buyButton = page.getByRole('button', { name: /Buy for/ }).last();
  await expect(buyButton).toBeVisible();
  await buyButton.click();
}

async function approveAsBuyer(page: import('@playwright/test').Page) {
  const authorizeButton = page.getByRole('button', { name: /^Approve/ }).last();
  await expect(authorizeButton).toBeVisible();
  await authorizeButton.click();
}

async function executePayment(page: import('@playwright/test').Page) {
  const readyButton = page.getByRole('button', {
    name: 'Continue to secure payment',
  }).last();
  await expect(readyButton).toBeVisible();
  await readyButton.click();

  const payButton = page.getByRole('button', {
    name: 'Continue to payment',
  }).last();
  await expect(payButton).toBeVisible();
  await payButton.click();

  await expect(page.getByText('Recovering payment status').last()).toBeVisible();
  await expect(page.getByLabel('Audit timeline').last()).toBeVisible();
}

test('merchant-configured automatic and manual buyer journeys', async ({ context }) => {
  const merchantPage = await context.newPage();
  await merchantPage.goto('/merchant/products/prod_001');

  // Merchant-owned catalog fields remain the authority for buyer-visible money.
  const price = merchantPage.getByLabel('Price (INR)');
  const stock = merchantPage.getByLabel('Stock');
  await expect(price).toHaveValue('1000');
  await price.fill('1200');
  await stock.fill('40');
  await merchantPage.getByRole('button', { name: 'Save changes' }).click();
  await expect(merchantPage.getByText('Your changes were saved as a new product version.')).toBeVisible();

  // Configure automatic acceptance above the product's trusted price.
  await merchantPage.goto('/merchant/policy');
  await merchantPage.getByRole('radio', {
    name: /Automatically accept below a limit/,
  }).click();
  await merchantPage.getByLabel('Maximum amount (INR)').fill('2500');
  await merchantPage.getByRole('button', { name: 'Save policy' }).click();
  await expect(merchantPage.getByText('Policy saved')).toBeVisible();

  const buyerPage = await context.newPage();
  await buyerPage.goto('/buyer');
  await submitBuyerSearch(buyerPage);
  await expect(buyerPage.getByRole('button', { name: 'Approve ₹1,200' })).toBeVisible();
  await approveAsBuyer(buyerPage);
  await expect(buyerPage.getByText('Automatically accepted').last()).toBeVisible();
  await executePayment(buyerPage);

  // Switch the same merchant to independent manual approval.
  await merchantPage.goto('/merchant/policy');
  await merchantPage.getByRole('radio', { name: /Review every purchase/ }).click();
  await merchantPage.getByRole('button', { name: 'Save policy' }).click();
  await expect(merchantPage.getByText('Policy saved')).toBeVisible();

  await submitBuyerSearch(buyerPage);
  await approveAsBuyer(buyerPage);
  await expect(buyerPage.getByText('Merchant review required').last()).toBeVisible();

  // Full reload proves the review came from the database, not shared UI state.
  await merchantPage.goto('/merchant/review');
  const merchantApprove = merchantPage.getByRole('button', { name: 'Approve' }).last();
  await expect(merchantApprove).toBeVisible();
  await merchantApprove.click();
  await expect(merchantPage.getByText('Approved proposal for Premium Coffee Maker.')).toBeAttached();

  await buyerPage.getByRole('button', { name: 'Check merchant decision' }).last().click();
  await expect(buyerPage.getByText('Approved by merchant').last()).toBeVisible();
  await executePayment(buyerPage);

  await expect(buyerPage.getByLabel('Audit timeline')).toHaveCount(2);
});
