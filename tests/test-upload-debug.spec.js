import { test, expect } from '@playwright/test';
import path from 'path';

test('debug file upload with network monitoring', async ({ page }) => {
  // Enable console logging
  page.on('console', msg => console.log('Browser console:', msg.text()));
  page.on('pageerror', error => console.log('Page error:', error));
  
  // Monitor network requests
  page.on('request', request => {
    if (request.url().includes('transcribe')) {
      console.log('>> Request to /transcribe:', request.method(), request.url());
    }
  });
  
  page.on('response', response => {
    if (response.url().includes('transcribe')) {
      console.log('<< Response from /transcribe:', response.status(), response.statusText());
    }
  });
  
  // Navigate to the app
  await page.goto('http://localhost:50263');
  console.log('✓ Navigated to app');

  // Add debugging to the uploadFile function
  await page.evaluate(() => {
    const originalUploadFile = window.uploadFile;
    window.uploadFile = function(file) {
      console.log('uploadFile called with file:', file.name, 'size:', file.size, 'type:', file.type);
      return originalUploadFile.call(this, file);
    };
    
    // Also debug the XMLHttpRequest
    const originalSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function(data) {
      console.log('XMLHttpRequest.send called');
      if (data instanceof FormData) {
        console.log('Sending FormData');
      }
      return originalSend.call(this, data);
    };
  });

  // Ensure drop zone is visible
  const dropZone = page.locator('#drop-zone');
  await expect(dropZone).toBeVisible();
  console.log('✓ Drop zone is visible');

  // Use the available audio file
  const filePath = path.resolve('Fairfield Dr 16.m4a');
  console.log('Using file:', filePath);

  // Upload the file via the click-triggered input
  const [fileChooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    dropZone.click()
  ]);
  
  console.log('File chooser opened, setting file...');
  await fileChooser.setFiles(filePath);
  console.log('✓ File set in chooser');

  // Wait to see console logs
  await page.waitForTimeout(3000);
  
  // Check the result
  const result = page.locator('#result');
  const resultText = await result.textContent();
  console.log('Result text after 3s:', resultText);
  
  // Check if there's an error in the console
  const errors = await page.evaluate(() => {
    return window.lastError || null;
  });
  if (errors) {
    console.log('JavaScript errors:', errors);
  }
  
  // Take a screenshot
  await page.screenshot({ path: 'test-debug.png', fullPage: true });
  console.log('Screenshot saved as test-debug.png');
});

test.setTimeout(60000);
