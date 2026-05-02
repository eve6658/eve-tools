const puppeteer = require('puppeteer-core');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--window-size=1920,1080'
    ]
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

  console.log('Opening ECP portal...');
  await page.goto('https://ecp.sgcc.com.cn/ecp2.0/portal/#/', {
    waitUntil: 'networkidle2',
    timeout: 60000
  });

  // Wait for SPA to render
  await new Promise(r => setTimeout(r, 8000));

  // Get page title and content
  const title = await page.title();
  console.log('Title:', title);

  // Take screenshot
  await page.screenshot({ path: '/home/adam/.openclaw/workspace/ecp_portal.png', fullPage: false });
  console.log('Screenshot saved');

  // Get all text content
  const bodyText = await page.evaluate(() => document.body.innerText);
  console.log('Body text length:', bodyText.length);
  console.log('Body text:', bodyText.substring(0, 2000));

  // Look for search-related elements
  const searchElements = await page.evaluate(() => {
    const inputs = Array.from(document.querySelectorAll('input'));
    const buttons = Array.from(document.querySelectorAll('button'));
    const links = Array.from(document.querySelectorAll('a'));
    return {
      inputs: inputs.map(i => ({ placeholder: i.placeholder, type: i.type, id: i.id, name: i.name })),
      buttons: buttons.map(b => ({ text: b.innerText, id: b.id, class: b.className })),
      links: links.slice(0, 20).map(l => ({ text: l.innerText, href: l.href }))
    };
  });

  console.log('\nSearch elements:', JSON.stringify(searchElements, null, 2));

  await browser.close();
})().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
