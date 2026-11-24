/* Run make_browser_fixtures.py and serve a built Pages directory first. */
'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const {chromium} = require('playwright');

const base = process.env.EASE_PAGES_URL || 'http://127.0.0.1:8790/ease-sediment-volume-explorer/';
const qa = path.join(__dirname, '..', 'qa', 'pages');
const fixtures = path.join(qa, 'fixtures');
const view = (page, name) => page.locator('[data-view="' + name + '"]');
const screenshot = (page, name) => page.screenshot({path:path.join(qa, name)});
const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-6, `${a} differs from ${b}`);

async function finished(page, selector) {
  await page.waitForFunction(target => {
    const result = document.querySelector(target);
    return !result.hidden || !document.querySelector('#form-error').hidden;
  }, selector, {timeout:120000});
  assert.equal(await page.locator('#form-error').isVisible(), false, await page.locator('#form-error').textContent());
}
async function save(page, selector) {
  const pending = page.waitForEvent('download');
  await page.locator(selector).click();
  return await pending;
}
async function summary(page) {
  const file = await save(page, '#export-summary');
  return JSON.parse(fs.readFileSync(await file.path(), 'utf8'));
}

(async () => {
  fs.mkdirSync(qa, {recursive:true});
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_EXECUTABLE || '/usr/bin/google-chrome',
    args:['--no-sandbox','--enable-unsafe-swiftshader','--no-proxy-server']
  });
  const context = await browser.newContext({viewport:{width:1440,height:1000}, acceptDownloads:true});
  const page = await context.newPage();
  const errors = [];
  const sends = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error' && message.text().startsWith('EASE browser worker')) {
      console.error(message.text());
    }
  });
  page.on('request', request => {if (request.method() !== 'GET') sends.push(request.url());});
  try {
    await page.goto(base);
    await page.keyboard.press('Tab');
    assert.match(await page.locator(':focus').textContent(), /Skip to content/i);
    await page.locator('[data-stat="above"]').getByText('2,616.7 m³', {exact:true}).waitFor();
    assert.ok(await page.locator('.hero-figure img').evaluate(img => img.complete && img.naturalWidth));
    assert.equal(new URL(await page.getByRole('link', {name:'Bathymetry source'}).getAttribute('href')).hostname, 'maps.rijkswaterstaat.nl');
    await page.getByRole('link', {name:'Build information'}).click();
    await page.getByRole('heading', {name:'Build information',exact:true}).waitFor();
    assert.match(await page.locator('main code').textContent(), /^[a-f0-9]{40}$/);
    await page.goBack();
    await page.getByRole('link', {name:'Try the public example'}).click();
    await page.waitForFunction(() => document.querySelector('#chart')?.data?.[0]?.type === 'surface');
    assert.equal(await page.locator('#metric-above').textContent(),'2,616.7');
    assert.equal((await save(page, '#export-bundle')).suggestedFilename(),'bundle.zip');

    await page.goto(base);
    await screenshot(page,'desktop-home.png');
    await page.getByRole('link', {name:'Analyse your own survey'}).click();
    await page.locator('#survey-drop').waitFor();
    assert.equal(await page.locator('#survey-file').isEnabled(), true);
    assert.equal(await page.locator('input[type=password]').count(), 0);
    await screenshot(page,'direct-upload.png');

    const rows = ['x,y,z'];
    for (let x=0;x<=4;x++) for (let y=0;y<=4;y++) rows.push(`${x},${y},${1+x/10+y/100}`);
    const dataTransfer = await page.evaluateHandle(csv => {
      const transfer = new DataTransfer();
      transfer.items.add(new File([csv], 'synthetic-survey.csv', {type:'text/csv'}));
      return transfer;
    }, rows.join('\n'));
    await page.locator('#survey-drop').dispatchEvent('drop',{dataTransfer});
    await dataTransfer.dispose();
    assert.equal(await page.locator('#survey-name').textContent(),'synthetic-survey.csv');
    await page.locator('#inspect-survey').click();
    await finished(page,'#survey-preview');

    await page.locator('#reference-mode').selectOption('constant');
    await page.locator('#reference-elevation').fill('0');
    await page.locator('#reference-note').fill('Synthetic flat design');
    await page.locator('#surface-method').selectOption('kriging');
    await page.locator('#kriging-model').selectOption('gaussian');
    await page.locator('#kriging-fit').selectOption('manual');
    await page.locator('#kriging-range').fill('7');
    await page.locator('#kriging-fields details summary').click();
    await page.locator('#kriging-neighbors').fill('8');
    await page.locator('#kriging-radius').fill('10');
    await page.locator('#run-analysis').click();
    await finished(page,'#results');
    await view(page,'uncertainty').click();
    const run = await summary(page);
    assert.equal(run.provenance.configuration.kriging_range,7);
    assert.equal(run.provenance.configuration.kriging_neighbors,8);
    assert.equal(run.provenance.configuration.kriging_radius,10);
    close(run.summary.valid_area_m2,16);
    await screenshot(page,'browser-own-survey-kriging.png');
    await page.locator('[data-language=nl]').click();
    assert.match(await page.locator('#runtime-footer').textContent(), /Analyse in de browser/);
    await page.locator('[data-language=en]').click();

    await page.locator('#survey-file').setInputFiles(path.join(fixtures,'survey.zip'));
    await page.locator('#inspect-survey').click();
    await finished(page,'#survey-preview');
    assert.match(await page.locator('#survey-preview').textContent(), /25/);

    await page.locator('#reference-type').selectOption('previous');
    await page.locator('#reference-file').setInputFiles(path.join(fixtures,'survey.zip'));
    await page.locator('#reference-note').fill('Same synthetic PointZ survey');
    await page.locator('#surface-method').selectOption('tin');
    await page.locator('#run-analysis').click();
    await finished(page,'#results');
    const pointz = await summary(page);
    close(pointz.summary.valid_area_m2,16);
    close(pointz.summary.positive_volume_m3,0);
    close(pointz.summary.negative_volume_m3,0);

    await page.locator('#reference-type').selectOption('design');
    await page.locator('#survey-file').setInputFiles(path.join(fixtures,'compressed.tif'));
    await page.locator('#inspect-survey').click();
    await finished(page,'#survey-preview');
    assert.match(await page.locator('#survey-preview').textContent(), /24/);
    await page.locator('#reference-mode').selectOption('constant');
    await page.locator('#reference-elevation').fill('-3');
    await page.locator('#reference-note').fill('Synthetic raster comparison');
    await page.locator('#surface-method').selectOption('tin');
    await page.locator('#run-analysis').click();
    await finished(page,'#results');
    const geotiff = await save(page,'#export-geotiff');
    await geotiff.saveAs(path.join(qa,'browser-difference.tif'));

    await page.locator('#survey-file').setInputFiles(path.join(fixtures,'paired-survey.csv'));
    await page.locator('#survey-preprocess').check();
    await page.locator('#survey-sounding').setInputFiles(path.join(fixtures,'SNDG00001'));
    await page.locator('#inspect-survey').click();
    await finished(page,'#survey-preview');
    assert.match(await page.locator('#survey-preview').textContent(), /Soundings excluded for missing corrections1/);
    assert.match(await page.locator('#survey-preview').textContent(), /4/);
    await page.locator('#survey-preprocess').uncheck();

    if (process.env.EASE_BROWSER_LARGE) {
      const file = process.env.EASE_BROWSER_LARGE;
      assert.equal(fs.statSync(file).size,104857600);
      await page.locator('#survey-file').setInputFiles(file);
      await page.locator('#inspect-survey').click();
      await finished(page,'#survey-preview');
      console.log('100 MiB file inspected in the browser');
    }

    await page.locator('#load-demo').click();
    await page.locator('#demo-source').waitFor();
    await page.locator('#surface-method').selectOption('tin');
    await page.locator('#run-analysis').click();
    await finished(page,'#results');
    const tin = await summary(page);
    close(tin.summary.positive_volume_m3,2616.6737851464727);
    close(tin.summary.negative_volume_m3,829.9073631364955);
    await page.locator('#surface-method').selectOption('kriging');
    await page.locator('#kriging-fit').selectOption('auto');
    // Restore defaults after tuning the manual example.
    await page.locator('#kriging-model').selectOption('spherical');
    if (!(await page.locator('#kriging-fields details').getAttribute('open') !== null)) {
      await page.locator('#kriging-fields details summary').click();
    }
    await page.locator('#kriging-neighbors').fill('16');
    await page.locator('#kriging-radius').fill('20');
    await page.locator('#run-analysis').click();
    await finished(page,'#results');
    const kriging = await summary(page);
    close(kriging.summary.positive_volume_m3,2598.930731656686);
    close(kriging.summary.negative_volume_m3,812.663903790143);

    const mobile = await browser.newPage({viewport:{width:390,height:844}, isMobile:true, hasTouch:true, deviceScaleFactor:1});
    await mobile.goto(base);
    await mobile.getByRole('link',{name:'Analyse your own survey'}).click();
    await mobile.locator('#survey-drop').waitFor();
    assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await screenshot(mobile,'mobile-explorer.png');
    await mobile.close();
    assert.deepEqual(errors,[]);
    assert.deepEqual(sends,[], 'Browser runtimes must not POST survey data');
    console.log('Direct upload, browser TIN/Kriging, PointZ, compressed GeoTIFF, paired SND, exports and mobile passed');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
