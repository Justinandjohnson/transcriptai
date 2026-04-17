import { test, expect } from '@playwright/test';
import path from 'path';

test('should upload and transcribe an audio file', async ({ page }) => {
  // Navigate to the app - using the actual running port
  await page.goto('http://localhost:50263');

  // Ensure drop zone is visible
  const dropZone = page.locator('#drop-zone');
  await expect(dropZone).toBeVisible();

  // Use the available audio file
  const filePath = path.resolve('Fairfield Dr 16.m4a');

  // Upload the file via the click-triggered input
  const [fileChooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    dropZone.click()
  ]);
  await fileChooser.setFiles(filePath);

  // Wait for the progress container to appear and then disappear (indicating completion)
  const progressContainer = page.locator('#progress-container');
  await expect(progressContainer).toBeVisible({ timeout: 5000 });
  
  // Wait for transcription to complete - the result should have text
  const result = page.locator('#result');
  await expect(result).not.toHaveText('', { timeout: 60000 });
  await expect(result).not.toHaveText('Uploading file...', { timeout: 60000 });

  // Check that GPT sections are generated
  const gptNotes = page.locator('#gpt-notes');
  const gptSummary = page.locator('#gpt-summary');
  const gptActionItems = page.locator('#gpt-action-items');
  
  await expect(gptNotes).not.toHaveText('', { timeout: 30000 });
  await expect(gptSummary).not.toHaveText('', { timeout: 30000 });
  await expect(gptActionItems).not.toHaveText('', { timeout: 30000 });

  console.log('✓ Transcription completed successfully');
  console.log('Transcription text:', await result.textContent());
  console.log('GPT Notes:', await gptNotes.textContent());
  console.log('GPT Summary:', await gptSummary.textContent());
  console.log('GPT Action Items:', await gptActionItems.textContent());
});
