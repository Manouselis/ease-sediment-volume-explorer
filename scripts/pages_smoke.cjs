/* Run with Playwright installed. EASE_PAGES_URL points at a served Pages build. */
'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const {chromium} = require('playwright');

const base = process.env.EASE_PAGES_URL || 'http://127.0.0.1:8790/ease-sediment-volume-explorer/';
const protectedKey = process.env.EASE_BROWSER_TEST_KEY;
const qa = path.join(__dirname, '..', 'qa', 'pages');
const profiles = path.join(__dirname, '..', 'data');
const view = (page, name) => page.locator('[data-view="' + name + '"]');
const screenshot = (page, name) => page.screenshot({path:path.join(qa, name)});

(async () => {
  fs.mkdirSync(qa, {recursive:true});
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_EXECUTABLE || '/usr/bin/google-chrome',
    args:['--no-sandbox','--enable-unsafe-swiftshader','--no-proxy-server'],
  });
  const context = await browser.newContext({viewport:{width:1440,height:1000}, acceptDownloads:true});
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto(base);
    assert.match(await page.title(), /Sediment Volume Explorer/);
    await page.keyboard.press('Tab');
    assert.match(await page.locator(':focus').textContent(), /Skip to content/i);
    await page.locator('[data-stat="above"]').getByText('2,616.7 m³', {exact:true}).waitFor();
    if (!process.env.EASE_CAPTURE_IMAGE) {
      assert.ok(await page.locator('.hero-figure img').evaluate(img => img.complete && img.naturalWidth));
      await page.locator('main').click({position:{x:5,y:5}});
      await screenshot(page,'desktop-home.png');
    }
    const source = page.getByRole('link', {name:'Bathymetry source'});
    assert.equal(new URL(await source.getAttribute('href')).hostname, 'maps.rijkswaterstaat.nl');
    await page.getByRole('link', {name:'Build information'}).click();
    await page.getByRole('heading', {name:'Build information',exact:true}).waitFor();
    assert.match(await page.locator('main code').textContent(), /^[a-f0-9]{40}$/);
    await page.goBack();
    await page.getByRole('link', {name:/try the public demo/i}).click();
    await page.waitForFunction(() => document.querySelector('#chart')?.data?.[0]?.type === 'surface');
    assert.equal(await page.locator('#metric-above').textContent(), '2,616.7');
    assert.equal(await page.locator('#analysis-form').isVisible(), false);
    const align = await page.locator('#hosted-tools').evaluate(panel => ({
      heading: panel.querySelector('h1').getBoundingClientRect().top,
      label: panel.querySelector('label').getBoundingClientRect().top,
      method: panel.querySelector('select').getBoundingClientRect(),
      button: panel.querySelector('#open-public-demo').getBoundingClientRect()
    }));
    assert.ok(Math.abs(align.heading - align.label) <= 2, 'Panel columns align at the top');
    assert.ok(Math.abs(align.method.bottom - align.button.bottom) <= 2, 'Desktop demo controls share a row');
    await page.evaluate(() => document.fonts.ready);
    await page.locator('#analysis-chart-card').screenshot({path:path.join(qa,'demo-bed-card.png')});
    await screenshot(page,'desktop-bed.png');
    const download = page.waitForEvent('download');
    await page.locator('#export-bundle').click();
    assert.equal((await download).suggestedFilename(), 'bundle.zip');
    await view(page,'difference').click();
    await page.waitForFunction(() => document.querySelector('#chart')?.data?.[0]?.type === 'heatmap');
    await screenshot(page,'desktop-difference.png');
    await page.locator('#hosted-method').selectOption('kriging');
    await page.waitForFunction(() => document.querySelector('#uncertainty-view').getAttribute('aria-pressed') === 'true');
    assert.match(await page.locator('#resolved-method').textContent(), /Ordinary Kriging/);
    await page.locator('[data-language=nl]').click();
    assert.equal(await page.locator('html').getAttribute('lang'), 'nl');
    assert.match(await page.locator('#hosted-title').textContent(), /Openbare demo/);
    await screenshot(page,'desktop-uncertainty-nl.png');
    await page.reload();
    await page.waitForFunction(() => document.querySelector('#uncertainty-view').getAttribute('aria-pressed') === 'true');
    assert.equal(new URL(page.url()).searchParams.get('demo'), 'kriging');
    assert.equal(await page.locator('html').getAttribute('lang'), 'nl');

    const mobile = await browser.newPage({viewport:{width:390,height:844}, isMobile:true, hasTouch:true, deviceScaleFactor:1});
    await mobile.goto(base);
    assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await screenshot(mobile, 'mobile-home.png');
    await mobile.getByRole('link',{name:/try the public demo/i}).click();
    await mobile.waitForFunction(() => document.querySelector('#chart')?.data?.[0]?.type === 'surface');
    assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await screenshot(mobile,'mobile-explorer.png');
    await mobile.close();

    if (protectedKey) {
      await page.locator('[data-language=en]').click();
      await page.locator('#hosted-method').selectOption('tin');
      await view(page,'bed').waitFor();
      await page.locator('#hosted-access summary').click();
      await page.locator('#hosted-key').fill('bad-local-test-key');
      await page.locator('#hosted-login button').click();
      await page.getByRole('status').filter({hasText:/Access denied/}).waitFor();
      await page.locator('#hosted-key').fill(protectedKey);
      await page.locator('#hosted-login button').click();
      await page.locator('#load-demo').waitFor();
      assert.equal(await page.locator('#hosted-key').inputValue(),'');
      await page.locator('#survey-file').setInputFiles(path.join(profiles,'demo_current.csv'));
      await page.locator('#inspect-survey').click();
      await page.locator('#survey-preview').waitFor();
      await page.locator('#load-demo').click();
      await page.locator('#demo-source').waitFor();
      await page.locator('#run-analysis').click();
      await page.locator('#export-summary').waitFor();
      assert.equal(await page.locator('#metric-above').textContent(),'2,616.7');
      const url = await page.locator('#export-summary').getAttribute('href');
      assert.equal((await page.request.get(url, {headers:{Authorization:'Bearer ease-local-other-key'}})).status(),404);
      assert.equal((await page.request.get(url)).status(),401);
      const filePromise = page.waitForEvent('download');
      await page.locator('#export-summary').click();
      const file = await filePromise;
      const saved = JSON.parse(fs.readFileSync(await file.path(),'utf8'));
      assert.ok(Math.abs(saved.summary.positive_volume_m3 - 2616.673785) < 1e-5);
      await page.locator('#hosted-lock').click();
      await page.waitForFunction(() => document.querySelector('#analysis-form').parentElement.hidden);
      assert.equal(await page.locator('#survey-file').inputValue(),'');
      assert.equal(await page.locator('#export-summary').getAttribute('href'),'demo/tin/summary.json');
      await page.route('**/api/access', route => route.abort());
      if (!(await page.locator('#hosted-access').getAttribute('open') !== null)) await page.locator('#hosted-access summary').click();
      await page.locator('#hosted-key').fill(protectedKey);
      await page.locator('#hosted-login button').click();
      await page.getByRole('status').filter({hasText:/server is unavailable/}).waitFor();
    }
    assert.deepEqual(errors, []);
    console.log('Pages desktop, keyboard, mobile, language, chart, refresh and downloads passed' + (protectedKey ? ' with protected API checks' : ''));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
