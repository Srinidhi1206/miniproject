import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  // Navigate to scanner
  await page.goto('http://localhost:3000/#scan');
  
  // Take screenshot of URL tab
  await page.click('text=Link');
  await page.screenshot({ path: 'url_input.png' });

  // Take screenshot of QR tab
  await page.click('text=QR code');
  await page.screenshot({ path: 'qr_input.png' });
  
  // Go back to Message tab
  await page.click('text=Message');
  
  // Fill the textarea
  await page.fill('textarea', 'Warning: Your account is locked. Click here to verify: http://evil.com');
  
  // Click analyze
  await page.click('text=Analyze message');
  
  // Wait for loading state (short delay)
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'loading.png' });
  
  // Wait for result page
  await page.waitForSelector('text=Risk score', { timeout: 15000 });
  await page.screenshot({ path: 'result.png', fullPage: true });

  await browser.close();
})();
