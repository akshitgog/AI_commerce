import { test, expect } from '@playwright/test';

test('debug', async ({ page }) => {
  await page.goto('http://127.0.0.1:3000/buyer');
  await page.locator('input[placeholder*="Ask about products"]').fill('I need a coffee maker');
  await page.locator('input[placeholder*="Ask about products"]').press('Enter');
  
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'screenshot2.png' });
});
