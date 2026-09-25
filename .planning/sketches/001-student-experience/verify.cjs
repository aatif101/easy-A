// Browser review harness; dependencies stay outside the production web package.
// See README.md for environment and invocation. Preview server must be running.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const AxeBuilder = require('@axe-core/playwright').default;
const base = process.env.SKETCH_URL || 'http://127.0.0.1:4173/001-student-experience';
const evidence = { checked_at: new Date().toISOString(), renderings: [], checks: [], violations: [] };
const states = ['discovery', 'search', 'grades', 'section', 'limited', 'unavailable', 'empty'];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ permissions: ['clipboard-read', 'clipboard-write'] });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  const open = async (variant, state = 'discovery') => {
    await page.goto(`${base}/experience.html?variant=${variant}&state=${state}`);
    await page.locator('#result-count').waitFor();
  };
  for (const variant of ['guide', 'compact']) {
    for (const [device, width, height] of [['desktop', 1440, 1000], ['mobile', 390, 844]]) {
      await page.setViewportSize({ width, height });
      for (const state of states) {
        await open(variant, state);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${variant}/${device}/${state} overflows`);
        const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
        evidence.violations.push(...axe.violations.map(v => ({ variant, device, state, id: v.id, nodes: v.nodes.map(n => n.target) })));
        const screenshot = state === 'discovery' ? `${variant}-${device}.png` : `${variant}-${device}-${state}.png`;
        await page.screenshot({ path: path.join(__dirname, 'screenshots', screenshot), fullPage: ['grades', 'section'].includes(state) });
        const first = await page.locator('.course').count() ? await page.locator('.course').first().boundingBox() : null;
        evidence.renderings.push({ variant, device, state, width, height, first_course_y: first?.y ?? null, screenshot });
        if (state === 'discovery') {
          const codes = await page.locator('.course').evaluateAll(nodes => nodes.map(n => n.dataset.code));
          assert.equal(new Set(codes).size, codes.length);
          assert.equal(codes.length, 7);
          if (device === 'mobile') {
            const denominator = await page.locator('.evidence > p').first().boundingBox();
            assert(denominator.y + denominator.height < height, 'Denominator must fit first phone screen');
            if (variant === 'guide') {
              const action = await page.locator('.course-details summary').first().boundingBox();
              assert(action.y + action.height <= height, 'Guide course action must fit first phone screen');
            }
          }
        }
      }
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await open(variant);
    await page.getByRole('searchbox').fill('College Algebra');
    assert.equal(await page.locator('.course').count(), 1);
    assert.match(await page.locator('.evidence').innerText(), /1,534 of 3,200/);
    const summary = page.locator('.course-details > summary');
    await summary.focus();
    const outline = await summary.evaluate(el => getComputedStyle(el).outlineStyle);
    assert.notEqual(outline, 'none');
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('.course-details').getAttribute('open'), '');
    assert.equal(await page.getByRole('radio').count(), 5);
    const radio = page.getByRole('radio').first();
    await radio.check();
    const crn = await radio.inputValue();
    assert.match(await page.locator('.chosen').innerText(), new RegExp(crn));
    await page.getByRole('button', { name: 'Copy CRN', exact: true }).click();
    await page.getByRole('button', { name: 'CRN copied' }).waitFor();
    assert.equal(await page.evaluate(() => navigator.clipboard.readText()), crn);
    await summary.focus();
    await page.keyboard.press('Space');
    assert.equal(await page.locator('.course-details').getAttribute('open'), null);
    await page.getByRole('searchbox').fill('THE3111');
    assert.equal(await page.locator('.course').getAttribute('data-code'), 'THE 3111');
    assert.equal(await page.locator('#level-chip').isVisible(), false);
    await page.getByRole('searchbox').fill('');
    assert.equal(await page.locator('.course').count(), 7);
    await page.locator('#requirement').selectOption('SGEM');
    assert.equal(await page.locator('.course').getAttribute('data-code'), 'MAC 1105');
    await page.locator('#requirement').selectOption('all');
    await page.getByRole('button', { name: 'More filters' }).click();
    await page.locator('#level').selectOption('all');
    assert.equal(await page.locator('.course').count(), 8);
    await page.locator('#format').selectOption('CL');
    await page.getByRole('searchbox').fill('MAC 1105');
    await summary.click();
    assert.equal(await page.getByRole('radio').count(), 4);
    await open(variant);
    await page.locator('#sort').selectOption('title');
    assert.equal(await page.locator('.course').first().getAttribute('data-code'), 'AMH 2020');
    await page.locator('#sort').selectOption('history');
    assert.equal(await page.locator('.course').first().getAttribute('data-code'), 'ENC 1101');
    await page.getByRole('button', { name: 'How ranking works' }).click();
    assert.equal(await page.locator('#ranking-note').isVisible(), true);
    await open(variant, 'limited');
    assert.match(await page.locator('.outcome').innerText(), /80%[\s\S]*Limited history/);
    assert.match(await page.locator('.evidence').innerText(), /4 of 5/);
    await open(variant, 'unavailable');
    assert.equal(await page.locator('.percent').count(), 0);
    await page.locator('.course-details summary').click();
    assert.equal(await page.locator('.score').count(), 0);
    await open(variant, 'empty');
    await page.getByRole('button', { name: 'Clear search & filters' }).click();
    assert.equal(await page.locator('.course').count(), 7);
    assert.equal(await page.getByRole('searchbox').evaluate(el => el === document.activeElement), true);
    for (const [width, height] of [[320, 800], [375, 812], [768, 1024], [844, 390]]) {
      await page.setViewportSize({ width, height });
      await open(variant, 'section');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `reflow ${width}`);
    }
    await page.emulateMedia({ reducedMotion: 'reduce' });
    assert.equal(await page.locator('button').first().evaluate(el => getComputedStyle(el).transitionDuration), '0s');
    await page.setViewportSize({ width: 390, height: 844 });
    await open(variant, 'section');
    await page.addStyleTag({ content: 'html { font-size: 200%; }' });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, '200% text reflow');
    await page.screenshot({ path: path.join(__dirname, 'screenshots', `${variant}-text-200.png`) });
    evidence.checks.push(`${variant}: search by code/title, full five-section MAC list, keyboard expand/collapse and focus, CRN copy, all-level direct search, level/GenEd/format filters, sorting, ranking explanation, honest limited/unavailable states, empty recovery, 320/375/768/844px reflow, reduced motion`);
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${base}/index.html`);
  await page.getByRole('button', { name: 'B · Compact comparison' }).click();
  await page.locator('#viewport').selectOption('mobile');
  await page.locator('#state').selectOption('limited');
  await page.frameLocator('#preview').getByText('Limited history', { exact: true }).waitFor();
  assert.equal(await page.locator('#preview').evaluate(el => el.offsetWidth), 390);
  await page.goto(`${base}/comparison.html`);
  await page.getByRole('button', { name: '390 × 844 phone' }).click();
  await page.waitForFunction(() => [...document.images].every(i => i.complete && i.naturalWidth === 390));
  evidence.checks.push('Review variant/state/viewport controls and before/after image dimensions');
  evidence.console_errors = errors;
  fs.writeFileSync(path.join(__dirname, 'verification.json'), JSON.stringify(evidence, null, 2) + '\n');
  await browser.close();
  assert.deepEqual(errors, []);
  assert.deepEqual(evidence.violations, []);
  console.log(`PASS: ${evidence.renderings.length} state/viewport renders, interaction and reflow checks; no axe violations or browser errors.`);
})().catch(error => { console.error(error); process.exit(1); });
