import { test, expect } from '@playwright/test';
import path from 'path';

test('debug file upload and transcription', async ({ page }) => {
  // Enable console logging
  page.on('console', msg => console.log('Browser console:', msg.text()));
  page.on('pageerror', error => console.log('Page error:', error));
  
  // Navigate to the app
  await page.goto('http://localhost:50263');
  console.log('✓ Navigated to app');

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
  await fileChooser.setFiles(filePath);
  console.log('✓ File selected');

  // Wait a bit to see what happens
  await page.waitForTimeout(2000);
  
  // Check the result text
  const result = page.locator('#result');
  const resultText = await result.textContent();
  console.log('Result text after 2s:', resultText);
  
  // Check if progress container is visible
  const progressContainer = page.locator('#progress-container');
  const isProgressVisible = await progressContainer.isVisible();
  console.log('Progress container visible:', isProgressVisible);
  
  // Wait for network activity to complete
  await page.waitForLoadState('networkidle', { timeout: 30000 });
  console.log('✓ Network idle');
  
  // Check result again
  const finalResultText = await result.textContent();
  console.log('Final result text:', finalResultText);
  
  // If still uploading, check for errors
  if (finalResultText === 'Uploading file...') {
    console.log('❌ Upload appears to be stuck');
    
    // Check network errors
    const networkErrors = await page.evaluate(() => {
      return window.performance.getEntriesByType('resource')
        .filter(entry => entry.name.includes('/transcribe'))
        .map(entry => ({
          name: entry.name,
          status: entry.responseStatus || 'unknown',
          duration: entry.duration
        }));
    });
    console.log('Network requests:', networkErrors);
  } else {
    console.log('✓ Upload completed');
    
    // Check GPT sections
    const gptNotes = await page.locator('#gpt-notes').textContent();
    const gptSummary = await page.locator('#gpt-summary').textContent();
    const gptActionItems = await page.locator('#gpt-action-items').textContent();
    
    console.log('GPT Notes:', gptNotes ? 'Generated' : 'Empty');
    console.log('GPT Summary:', gptSummary ? 'Generated' : 'Empty');
    console.log('GPT Action Items:', gptActionItems ? 'Generated' : 'Empty');
  }
  
  // Take a screenshot for debugging
  await page.screenshot({ path: 'test-result.png', fullPage: true });
  console.log('Screenshot saved as test-result.png');
});

// Set longer timeout for this test
test.setTimeout(60000);
