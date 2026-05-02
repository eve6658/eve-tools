const puppeteer = require('puppeteer-core');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

  // Intercept network requests to find form API
  const requests = [];
  page.on('request', req => {
    if (req.url().includes('api') || req.url().includes('form') || req.url().includes('apply') || req.url().includes('submit')) {
      requests.push({ url: req.url(), method: req.method() });
    }
  });

  console.log('Opening page...');
  await page.goto('https://100t.xiaomimimo.com', { waitUntil: 'networkidle2', timeout: 30000 });
  await new Promise(r => setTimeout(r, 3000));

  // Click the apply button
  console.log('Clicking apply button...');
  try {
    await page.click('button.styles_waitlistBtn__b115ff05');
    await new Promise(r => setTimeout(r, 3000));
    
    // Take screenshot after clicking
    await page.screenshot({ path: '/home/adam/.openclaw/workspace/mimo_form.png', fullPage: false });
    console.log('Screenshot saved');

    // Check for modal/form
    const formContent = await page.evaluate(() => {
      // Look for any new modal, dialog, or form that appeared
      const modals = document.querySelectorAll('[class*="modal"], [class*="dialog"], [class*="form"], [class*="popup"], [role="dialog"]');
      const results = [];
      modals.forEach(m => {
        results.push({
          tag: m.tagName,
          class: m.className,
          text: m.innerText?.substring(0, 500)
        });
      });
      
      // Also check for any new visible elements
      const allInputs = document.querySelectorAll('input, textarea, select');
      const formData = [];
      allInputs.forEach(i => {
        formData.push({
          type: i.type,
          name: i.name,
          placeholder: i.placeholder,
          id: i.id
        });
      });
      
      return { modals: results, inputs: formData, bodyText: document.body.innerText.substring(0, 2000) };
    });
    
    console.log('Form content:', JSON.stringify(formContent, null, 2));
  } catch (e) {
    console.log('Click error:', e.message);
  }

  console.log('\nIntercepted requests:', JSON.stringify(requests, null, 2));

  await browser.close();
})().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
