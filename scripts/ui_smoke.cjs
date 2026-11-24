/* Run after starting the application: NODE_PATH=/path/to/node_modules node scripts/ui_smoke.cjs
 * Optional: EASE_URL=http://127.0.0.1:8765 CHROME_EXECUTABLE=/usr/bin/google-chrome
 * Browser assertions use genuine bundled RWS data; the invalid CSV is a negative test only.
 */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const qa = path.join(root, 'qa');
const url = process.env.EASE_URL || 'http://127.0.0.1:8765';
const executablePath = process.env.CHROME_EXECUTABLE || (fs.existsSync('/usr/bin/google-chrome') ? '/usr/bin/google-chrome' : undefined);
const debug = message => {if(process.env.EASE_TEST_DEBUG) console.error(`[ui smoke] ${message}`);};
const readNumber = async (page, id) => Number((await page.locator(id).textContent()).replaceAll(',', ''));
const approximately = (actual, expected, label) => assert.ok(Math.abs(actual-expected) < 1e-9 * Math.max(1,Math.abs(expected)), `${label}: ${actual} != ${expected}`);
async function bedScene(page) {
  return page.locator('#chart').evaluate(node => {
    const scene=node.layout.scene, ranges={x:scene.xaxis.range,y:scene.yaxis.range,z:scene.zaxis.range};
    const spans=Object.fromEntries(Object.entries(ranges).map(([axis,range])=>[axis,range[1]-range[0]]));
    const summary=document.querySelector('#chart-summary');
    const factor=Number(summary.dataset.verticalScale || document.querySelector('#vertical-scale-note').dataset.factor || summary.textContent.match(/(\d+(?:[.,]\d+)?)\s*×/)?.[1]?.replace(',','.'));
    return {ranges,spans,aspect:scene.aspectratio,factor,summary:summary.textContent,camera:scene.camera,dragmode:scene.dragmode,
      zaxis:{visible:node._fullLayout.scene.zaxis.visible,showticklabels:node._fullLayout.scene.zaxis.showticklabels,title:node._fullLayout.scene.zaxis.title.text},
      zValues:JSON.stringify(node.data.map(trace=>trace.z)),contours:node.data[0].contours,
      metrics:Array.from(document.querySelectorAll('.metric-value')).map(node=>node.textContent),
      exports:Array.from(document.querySelectorAll('.export-card a')).map(node=>node.getAttribute('href'))};
  });
}
function assertBedGeometry(scene, expectedFactor) {
  assert.ok(Number.isFinite(scene.factor) && scene.factor>=1,'The visible factor must be a finite exaggeration of at least 1×.');
  if(expectedFactor!==undefined) approximately(scene.factor,expectedFactor,'Reported vertical exaggeration');
  // Compare scene geometry with metre ranges, rather than trusting the label alone.
  approximately((scene.aspect.z/scene.aspect.x)/(scene.spans.z/scene.spans.x),scene.factor,'Actual vertical exaggeration');
  approximately(scene.aspect.x/scene.aspect.y,scene.spans.x/scene.spans.y,'Horizontal metre proportions');
  assert.equal(scene.camera.projection.type,'perspective');
  assert.equal(scene.dragmode,'orbit');
  assert.equal(scene.zaxis.visible,true); assert.equal(scene.zaxis.showticklabels,true);
  assert.ok(scene.zaxis.title.trim().length>0,'The height axis must be labelled.');
  assert.ok(scene.contours?.z?.show,'Bed height contours must help reveal the 3D surface.');
}
async function completed(page) {
  await page.waitForFunction(() => !document.querySelector('#results').hidden || (!document.querySelector('#form-error').hidden && !document.querySelector('#run-analysis').disabled), null, {timeout:60000});
  assert.equal(await page.locator('#form-error').isVisible(), false, await page.locator('#form-error').textContent());
  await page.waitForFunction(() => !document.querySelector('#run-analysis').disabled);
  await page.waitForTimeout(400);
}
(async () => {
  fs.mkdirSync(qa, {recursive:true});
  const browser = await chromium.launch({headless:true, executablePath, args:['--no-sandbox']});
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const deadline=setTimeout(()=>{console.error('UI smoke exceeded its 180-second deadline.');void browser.close().finally(()=>process.exit(1));},180000);
  const errors=[]; let expectedValidationError=false;
  page.on('pageerror', error=>errors.push(error.message));
  page.on('console', message=>{
    if(message.type()!=='error') return;
    const expected422=expectedValidationError && message.location().url.endsWith('/api/analyze') && /422/.test(message.text());
    if(!expected422) errors.push(message.text());
  });
  try {
    await page.goto(url);
    const translationAudit=await page.evaluate(()=>{
      const flatten=(obj,prefix='')=>Object.entries(obj).flatMap(([key,value])=>typeof value==='object'?flatten(value,prefix+key+'.'):[prefix+key]);
      const en=flatten(window.EASE_I18N.en).sort(),nl=flatten(window.EASE_I18N.nl).sort();
      const bindings=Array.from(document.querySelectorAll('[data-i18n],[data-i18n-placeholder],[data-i18n-aria]')).flatMap(node=>['i18n','i18nPlaceholder','i18nAria'].filter(key=>node.dataset[key]).map(key=>node.dataset[key]));
      return {matching:JSON.stringify(en)===JSON.stringify(nl),missing:bindings.filter(key=>!en.includes(key)),keys:en.length,bindings:bindings.length};
    });
    assert.equal(translationAudit.matching,true);assert.deepEqual(translationAudit.missing,[]);
    await page.click('[data-language="en"]');
    await page.screenshot({path:path.join(qa,'desktop-empty.png')});
    await page.click('#load-demo');
    await page.waitForFunction(()=>!document.querySelector('#demo-source').hidden);
    assert.equal(await page.locator('#results').isVisible(),false,'Loading demo must not calculate automatically.');
    await page.click('#run-analysis'); await completed(page);
    const observed={positive_m3:await readNumber(page,'#metric-above'),negative_m3:await readNumber(page,'#metric-below'),coverage_percent:await readNumber(page,'#metric-coverage')};
    assert.ok(Math.abs(observed.positive_m3-2616.7)<.11);
    assert.ok(Math.abs(observed.negative_m3-829.9)<.11);
    assert.ok(Math.abs(observed.coverage_percent-97.8)<.11);
    await page.evaluate(()=>window.scrollTo(0,0));
    await page.screenshot({path:path.join(qa,'desktop-results-en.png')});
    const resultLink=await page.locator('#export-summary').getAttribute('href');
    const download=await page.request.get(new URL(resultLink,url).href);
    assert.equal(download.status(),200); assert.ok((await download.json()).summary.positive_volume_m3>2600);
    for(const view of ['bed','map','difference']){
      debug(`English chart ${view}`);
      await page.click(`[data-view="${view}"]`);
      await page.waitForTimeout(500);
      assert.equal(await page.locator(`[data-view="${view}"]`).getAttribute('aria-pressed'),'true');
      const trace=await page.locator('#chart').evaluate(node=>node.data?.[0]?.type);
      assert.equal(trace,{bed:'surface',map:'scattergl',difference:'heatmap'}[view]);
      assert.equal(await page.locator('#bed-controls').isVisible(),view==='bed','Vertical exaggeration controls belong to the 3D view only.');
    }
    await page.click('[data-view="bed"]'); await page.waitForTimeout(500);
    debug('Read automatic 3D scene');
    assert.equal(await page.locator('#vertical-scale').inputValue(),'auto','The first 3D view should reveal the shallow relief automatically.');
    assert.deepEqual(await page.locator('#vertical-scale option').evaluateAll(options=>options.map(option=>option.value)),['auto','1','5','10','20','50']);
    assert.match(await page.locator('label[for="vertical-scale"]').textContent(),/vertical|height/i);
    assert.match(await page.locator('#vertical-scale-note').textContent(),/display|visual/i);
    assert.match(await page.locator('#vertical-scale-note').textContent(),/volume/i);
    const autoScene=await bedScene(page); assertBedGeometry(autoScene);
    assert.ok(autoScene.factor>1,'The shallow RWS demo needs visible relief in Auto mode.');
    assert.ok(autoScene.aspect.z/Math.max(autoScene.aspect.x,autoScene.aspect.y)>=.1,'Auto mode must give the canal relief a visibly non-flat scene.');
    debug('Turn 3D camera before reset');
    // Real pointer orbit is visually checked separately; CDP drag can stall software WebGL.
    await page.evaluate(()=>{void Plotly.relayout(document.querySelector('#chart'),{'scene.camera.eye':{x:-1.2,y:1.5,z:.7}});});
    debug('Camera relayout dispatched');
    assert.notDeepEqual((await bedScene(page)).camera.eye,autoScene.camera.eye,'The 3D scene camera must be movable.');
    await page.click('#reset-bed-view'); await page.waitForTimeout(350);
    debug('Reset 3D camera');
    assert.deepEqual((await bedScene(page)).camera.eye,autoScene.camera.eye,'Reset view must restore the oblique camera.');
    const scaleChecks=[];
    for(const scale of ['1','5','10','20','50']){
      debug(`3D scale ${scale}`);
      await page.locator('#vertical-scale').selectOption(scale); await page.waitForTimeout(250);
      const scene=await bedScene(page); assertBedGeometry(scene,Number(scale));
      assert.equal(scene.zValues,autoScene.zValues,'Display scale must preserve actual metre elevations.');
      assert.deepEqual(scene.metrics,autoScene.metrics,'Display scale must preserve all numerical results.');
      assert.deepEqual(scene.exports,autoScene.exports,'Display scale must preserve downloadable results.');
      assert.deepEqual(scene.ranges,autoScene.ranges,'Display scale must preserve actual coordinate ranges.');
      assert.equal(await page.locator('#results').isVisible(),true);
      scaleChecks.push({selected:scale,factor:scene.factor,aspect:scene.aspect});
    }
    await page.locator('#vertical-scale').selectOption('auto'); await page.waitForTimeout(350);
    assertBedGeometry(await bedScene(page),autoScene.factor);
    await page.screenshot({path:path.join(qa,'desktop-bed-en.png')});
    await page.click('[data-language="nl"]');
    debug('Dutch chart controls');
    assert.equal(await page.locator('html').getAttribute('lang'),'nl');
    assert.equal(await page.locator('.workspace').getAttribute('aria-label'),'Analysewerkruimte');
    assert.equal(await page.locator('#results').isVisible(),true);
    assert.equal(await page.locator('#export-summary').getAttribute('href'),resultLink,'Language change must preserve results.');
    assert.match(await page.locator('#result-interpretation').textContent(),/baggervolume/);
    assert.match(await page.locator('#reference-note').inputValue(),/Aangenomen/);
    assert.match(await page.locator('#result-reference-note').textContent(),/Aangenomen/);
    assert.match(await page.locator('#warning-list').textContent(),/referentie|ontwerp/);
    for(const view of ['bed','map','difference']){
      await page.click(`[data-view="${view}"]`); await page.waitForTimeout(350);
      const label=await page.locator('#chart').getAttribute('aria-label');
      assert.equal(label,{bed:'Waterbodem · 3D',map:'Meetpunten',difference:'Verschilkaart'}[view]);
      const plotLabels=await page.locator('#chart').evaluate(node=>JSON.stringify({trace:node.data[0].hovertemplate,layout:node.layout.xaxis?.title,scene:node.layout.scene}));
      assert.match(plotLabels,/Hoogte|Oostcoördinaat/);
    }
    await page.click('[data-view="bed"]'); await page.waitForTimeout(500);
    assert.equal(await page.locator('#vertical-scale').inputValue(),'auto');
    assert.match(await page.locator('label[for="vertical-scale"]').textContent(),/vertical|hoogte/i);
    assert.match(await page.locator('#vertical-scale-note').textContent(),/weergave|visueel/i);
    assert.match(await page.locator('#vertical-scale-note').textContent(),/volume/i);
    assertBedGeometry(await bedScene(page),autoScene.factor);
    const metricBounds=await page.locator('.metric-card').evaluateAll(cards=>cards.map(card=>{const value=card.querySelector('.metric-value>span');const a=card.getBoundingClientRect(),b=value.getBoundingClientRect();return {value:value.textContent,cardRight:a.right,valueRight:b.right,cardWidth:a.width,valueWidth:b.width};}));
    assert.ok(metricBounds.every(item=>item.valueRight<item.cardRight-8),'Metric numbers must fit inside their cards.');
    await page.screenshot({path:path.join(qa,'desktop-bed-nl.png')});
    await page.setViewportSize({width:390,height:844});
    debug('Mobile viewport');
    await page.evaluate(()=>window.scrollTo(0,document.querySelector('.workspace').getBoundingClientRect().top+window.scrollY-14));
    await page.waitForTimeout(400);
    await page.screenshot({path:path.join(qa,'mobile-results-nl.png')});
    assert.equal(await page.locator('#bed-controls').isVisible(),true);
    assertBedGeometry(await bedScene(page),autoScene.factor);
    const mobileControlBounds=await page.locator('#vertical-scale').boundingBox();
    assert.ok(mobileControlBounds.x>=0 && mobileControlBounds.x+mobileControlBounds.width<=390,'Vertical-scale selector must fit on mobile.');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth),false,'No mobile horizontal overflow.');
    await page.setViewportSize({width:768,height:1024});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth),false,'No tablet horizontal overflow.');
    await page.setViewportSize({width:1440,height:1000});
    await page.click('[data-language="en"]');
    await page.locator('#reference-elevation').fill('-6.4');
    assert.match(await page.locator('#reference-note').inputValue(),/-6\.4/);
    assert.equal(await page.locator('#results').isVisible(),false);
    await page.locator('#reference-elevation').fill('-6.5');
    await page.locator('#cell-size').fill('2');
    assert.equal(await page.locator('#results').isVisible(),false);
    assert.equal(await page.locator('#export-summary').getAttribute('href'),null,'Old exports must be invalidated.');
    assert.equal(await page.locator('#stale-note').isVisible(),true);
    // Exercise a true file upload and reference-file path using the same genuine RWS heights.
    await page.locator('#survey-file').setInputFiles(path.join(root,'data','demo_current.csv'));
    debug('Real uploaded reference path');
    await page.locator('#reference-mode').selectOption('file');
    await page.locator('#reference-file').setInputFiles(path.join(root,'data','demo_reference.csv'));
    await page.locator('#reference-note').fill('Explicitly assumed design surface at -6.5 m NAP, not a measured sediment boundary.');
    await page.locator('#cell-size').fill('1');
    await page.click('#run-analysis'); await completed(page);
    assert.ok(Math.abs(await readNumber(page,'#metric-above')-2616.7)<.11);
    await page.locator('#reference-type').selectOption('previous');
    assert.equal(await page.locator('#reference-mode').inputValue(),'file');
    assert.equal(await page.locator('#reference-mode option[value="constant"]').isDisabled(),true);
    await page.locator('#survey-file').setInputFiles({name:'invalid.csv',mimeType:'text/csv',buffer:Buffer.from('wrong,columns\n1,2\n')});
    expectedValidationError=true;
    debug('Invalid CSV negative test');
    await page.click('#run-analysis');
    await page.waitForFunction(()=>!document.querySelector('#form-error').hidden);
    assert.match(await page.locator('#form-error').textContent(),/columns|coordinate/);
    assert.equal(await page.locator('#results').isVisible(),false);
    await page.click('[data-language="nl"]');
    assert.match(await page.locator('#form-error').textContent(),/kolom|coördinaat/);
    expectedValidationError=false;
    // Small synthetic display edge cases are separate from the real survey validation above.
    await page.click('[data-language="en"]');
    await page.locator('#reference-type').selectOption('design');
    await page.locator('#reference-mode').selectOption('constant');
    await page.locator('#reference-elevation').fill('-6.5');
    await page.locator('#filter-mode').selectOption('off');
    const edgeCases=[];
    for(const [name,height] of [['flat',()=>-6.5],['steep',(x,y)=>-6.5+40*y]]){
      debug(`Synthetic ${name} display case`);
      const rows=['x,y,z'];
      for(let y=0;y<10;y++) for(let x=0;x<10;x++) rows.push(`${133875+x},${455250+y},${height(x,y)}`);
      await page.locator('#survey-file').setInputFiles({name:`synthetic-${name}.csv`,mimeType:'text/csv',buffer:Buffer.from(rows.join('\n'))});
      await page.locator('#reference-note').fill(`Synthetic ${name} display edge case; not field data.`);
      await page.click('#run-analysis'); await completed(page);
      await page.click('[data-view="bed"]'); await page.waitForTimeout(350);
      const scene=await bedScene(page); assertBedGeometry(scene);
      assert.ok(scene.spans.z>0 && Number.isFinite(scene.spans.z),'A flat surface still requires a usable height-axis range.');
      assert.ok(Object.values(scene.aspect).every(value=>Number.isFinite(value)&&value>0),'All scene proportions must remain finite and positive.');
      if(name==='steep') approximately(scene.factor,1,'Auto must not compress naturally tall data');
      edgeCases.push({name,factor:scene.factor,zRange:scene.ranges.z,aspect:scene.aspect});
    }
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({status:'passed',observed,translationAudit,metricBounds,bed3d:{autoFactor:autoScene.factor,ranges:autoScene.ranges,aspect:autoScene.aspect,scaleChecks,edgeCases},checks:['real demo','all chart views EN/NL','3D perspective and labelled height axis','orbit enabled and reset restores changed camera','Auto reveals shallow relief','1× restores metre proportions','all scales preserve elevations, results and exports','3D-only controls EN/NL','translated error and ARIA','language retains results','stale exports removed','real CSV upload and reference file','invalid CSV rejected','mobile/tablet no overflow','flat and steep synthetic display cases','no unexpected browser console errors'],screenshots:qa},null,2));
  } finally { clearTimeout(deadline); await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
