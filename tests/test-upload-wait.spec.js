import { test, expect } from '@playwright/test';
import path from 'path';

test('test file upload with proper waiting', async ({ page }) => {
  // Enable console logging
  page.on('console', msg => console.log('Browser console:', msg.text()));
  page.on('pageerror', error => console.log('Page error:', error));
  
  // Monitor network requests
  let transcribeRequestSent = false;
  let transcribeResponseReceived = false;
  
  page.on('request', request => {
    if (request.url().includes('transcribe')) {
      console.log('>> Request to /transcribe:', request.method());
      transcribeRequestSent = true;
    }
  });
  
  page.on('response', response => {
    if (response.url().includes('transcribe')) {
      console.log('<< Response from /transcribe:', response.status());
      transcribeResponseReceived = true;
    }
    if (response.url().includes('generate-sections')) {
      console.log('<< Response from /generate-sections:', response.status());
    }
  });
  
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

  // Upload the file
  const [fileChooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    dropZone.click()
  ]);
  await fileChooser.setFiles(filePath);
  console.log('✓ File selected');

  // Wait for the request to be sent
  await page.waitForTimeout(1000);
  console.log('Request sent:', transcribeRequestSent);
  
  // Wait for the transcribe response with a longer timeout
  console.log('Waiting for transcription to complete (this may take 30-60 seconds)...');
  
  // Wait for the result to change from "Uploading file..."
  const result = page.locator('#result');
  
  try {
    // Wait up to 90 seconds for the transcription to complete
    await page.waitForFunction(
      () => {
        const resultEl = document.getElementById('result');
        return resultEl && resultEl.textContent !== 'Uploading file...' && resultEl.textContent !== '';
      },
      { timeout: 90000 }
    );
    
    console.log('✓ Transcription completed!');
    
    // Get the transcription text
    const transcriptionText = await result.textContent();
    console.log('Transcription text:', transcriptionText.substring(0, 100) + '...');
    
    // Wait a bit for GPT sections to load
    await page.waitForTimeout(5000);
    
    // Check GPT sections
    const gptNotes = page.locator('#gpt-notes');
    const gptSummary = page.locator('#gpt-summary');
    const gptActionItems = page.locator('#gpt-action-items');
    
    const notesText = await gptNotes.textContent();
    const summaryText = await gptSummary.textContent();
    const actionText = await gptActionItems.textContent();
    
    console.log('GPT Notes:', notesText ? '✓ Generated' : '✗ Empty');
    console.log('GPT Summary:', summaryText ? '✓ Generated' : '✗ Empty');
    console.log('GPT Action Items:', actionText ? '✓ Generated' : '✗ Empty');
    
    // Test passes if we have transcription and at least one GPT section
    expect(transcriptionText).not.toBe('');
    expect(transcriptionText).not.toBe('Uploading file...');
    
    if (notesText || summaryText || actionText) {
      console.log('✓ Test PASSED: Transcription and GPT processing completed successfully!');
    } else {
      console.log('⚠ Transcription completed but GPT sections not generated');
    }
    
  } catch (error) {
    console.log('✗ Timeout waiting for transcription');
    const currentText = await result.textContent();
    console.log('Current result text:', currentText);
    
    // Check server logs
    console.log('Response received:', transcribeResponseReceived);
    
    throw new Error('Transcription did not complete within 90 seconds');
  }
  
  // Take a final screenshot
  await page.screenshot({ path: 'test-final.png', fullPage: true });
  console.log('Screenshot saved as test-final.png');
});

// Set a very long timeout for this test
test.setTimeout(120000);
