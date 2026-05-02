const puppeteer = require('puppeteer-core');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--window-size=1920,1080']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

  console.log('Opening form...');
  await page.goto('https://100t.xiaomimimo.com', { waitUntil: 'networkidle2', timeout: 30000 });
  await new Promise(r => setTimeout(r, 3000));

  // Click apply button
  await page.click('button.styles_waitlistBtn__b115ff05');
  await new Promise(r => setTimeout(r, 3000));

  // Fill email
  const emailInput = await page.$('input[type="email"]');
  if (emailInput) {
    await emailInput.click();
    await emailInput.type('16082177@qq.com');
    console.log('Email filled');
  }

  // Click OpenClaw checkbox
  const checkboxes = await page.$$('label, [role="checkbox"], input[type="checkbox"]');
  for (const cb of checkboxes) {
    const text = await page.evaluate(el => el.innerText || el.textContent, cb);
    if (text && text.includes('OpenClaw')) {
      await cb.click();
      console.log('OpenClaw selected');
      break;
    }
  }

  // Click MiMo series checkbox
  for (const cb of checkboxes) {
    const text = await page.evaluate(el => el.innerText || el.textContent, cb);
    if (text && text.includes('MiMo')) {
      await cb.click();
      console.log('MiMo selected');
      break;
    }
  }

  // Fill project description
  const textarea = await page.$('textarea');
  if (textarea) {
    await textarea.click();
    const desc = `我构建了一个基于 OpenClaw + MiMo 的星象数学推演模型。紫微斗数是公元960年前后成型的数学体系——它用天干地支、阴阳五行作为变量，通过14主星在12宫位的排列组合，建立了一套描述人生轨迹的数学模型。其本质是一套多变量条件概率系统：出生时间确定初始条件（生辰八字），星曜运行构成约束条件，四化飞星提供状态转移函数。该系统将这套古老的数学结构编码为知识库，结合 MiMo 的推理能力，实现从初始条件推导出完整命盘。核心难点：1）长链推理——从排盘到解读涉及20+步逻辑推演，每一步都依赖前一步的输出；2）多变量耦合——14主星×12宫位×4化星×108星曜，变量空间巨大；3）知识库与推理模型的深度融合——将数千条星曜关系规则嵌入推理链。该项目探索古代数学体系如何用现代大语言模型的推理能力重新激活。`;
    await textarea.type(desc, { delay: 5 });
    console.log('Description filled');
  }

  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: '/home/adam/.openclaw/workspace/mimo_form_filled.png', fullPage: false });
  console.log('Screenshot saved - check before submitting');

  // DON'T click submit - let user verify first
  console.log('\nForm filled. Screenshot saved. DO NOT auto-submit.');

  await browser.close();
})().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
