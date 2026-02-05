/**
 * Comprehensive Fix Verification Test
 * Tests ALL 7 fixes across the Narrative Investment app.
 * Reports PASS/FAIL with specific data for each check.
 */
import { test, expect } from '@playwright/test';

const MOBILE_VIEWPORT = { width: 390, height: 844 };

test.describe.serial('Comprehensive Fix Verification', () => {
  let page;
  const results = [];

  function report(testName, checkName, pass, detail) {
    const entry = { testName, checkName, pass, detail };
    results.push(entry);
    const status = pass ? 'PASS' : 'FAIL';
    console.log(`[${status}] ${testName} > ${checkName}: ${detail}`);
  }

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext({ viewport: MOBILE_VIEWPORT });
    page = await context.newPage();
  });

  test.afterAll(async () => {
    console.log('\n\n');
    console.log('╔══════════════════════════════════════════════════════════════╗');
    console.log('║         COMPREHENSIVE FIX VERIFICATION REPORT               ║');
    console.log('╚══════════════════════════════════════════════════════════════╝');
    let passCount = 0;
    let failCount = 0;
    for (const r of results) {
      const icon = r.pass ? '✅' : '❌';
      console.log(`${icon} [${r.testName}] ${r.checkName}: ${r.detail}`);
      if (r.pass) passCount++;
      else failCount++;
    }
    console.log(`\n========== SUMMARY: ${passCount} PASSED, ${failCount} FAILED ==========`);
    await page.close();
  });

  // ==================== PRE-CONDITION: ONBOARDING ====================
  test('Pre-condition: Complete onboarding', async () => {
    await page.goto('/onboarding');
    await page.evaluate(() => localStorage.clear());
    await page.goto('/onboarding');
    await page.waitForLoadState('networkidle');

    // Click "다음" 4 times
    const nextBtn = page.locator('button', { hasText: /^다음$/ });
    for (let i = 0; i < 4; i++) {
      await nextBtn.click();
      await page.waitForTimeout(400);
    }

    // Select "입문"
    const beginnerBtn = page.locator('button:has-text("입문")');
    await beginnerBtn.click();
    await page.waitForTimeout(300);

    // Click "시작하기"
    const startBtn = page.locator('button', { hasText: /^시작하기$/ });
    await startBtn.click();
    await page.waitForTimeout(2000);

    const settings = await page.evaluate(() => {
      const s = localStorage.getItem('userSettings');
      return s ? JSON.parse(s) : null;
    });

    const pass = settings?.hasCompletedOnboarding === true;
    report('Onboarding', 'Completed', pass, `Settings: ${JSON.stringify(settings)}`);
    expect(pass).toBe(true);
  });

  // ==================== TEST 1: HOME PAGE UX ====================
  test('Test 1: Home page UX', async () => {
    await page.goto('/');
    await page.waitForTimeout(3000);
    await page.waitForLoadState('networkidle');

    await page.screenshot({ path: 'e2e/screenshots/t1-home.png', fullPage: true });

    // CHECK: Logo "History Mirror" is clickable (has cursor-pointer class)
    const logoEl = page.locator('h1:has-text("History Mirror")');
    await expect(logoEl).toBeVisible({ timeout: 5000 });
    const logoClasses = await logoEl.getAttribute('class');
    const logoHasCursorPointer = logoClasses?.includes('cursor-pointer') || false;
    const logoOnClick = await logoEl.evaluate(el => {
      // Check for onClick handler
      return el.onclick !== null || el.getAttribute('onclick') !== null;
    });
    report('Test 1', 'Logo cursor-pointer class', logoHasCursorPointer, `Classes: ${logoClasses}`);

    // CHECK: Bottom nav has ONLY 2 tabs
    const navBottom = page.locator('nav.nav-bottom, nav');
    const navButtons = navBottom.locator('button');
    const navTexts = await navButtons.allTextContents();
    const navTabTexts = navTexts.map(t => t.trim()).filter(t => t.length > 0);
    
    const has홈 = navTabTexts.some(t => t.includes('홈'));
    const has히스토리 = navTabTexts.some(t => t.includes('히스토리'));
    const has검색 = navTabTexts.some(t => t.includes('검색'));
    const has프로필 = navTabTexts.some(t => t.includes('프로필'));
    const onlyTwoTabs = has홈 && has히스토리 && !has검색 && !has프로필;
    report('Test 1', 'Bottom nav ONLY 2 tabs (홈+히스토리)', onlyTwoTabs, `Tabs found: ${navTabTexts.join(', ')} | 검색: ${has검색}, 프로필: ${has프로필}`);

    // CHECK: Keyword cards displayed with real data
    const keywordCards = await page.evaluate(() => {
      const cards = [];
      document.querySelectorAll('h3').forEach(h3 => {
        const text = h3.textContent.trim();
        if (text.length > 0) cards.push(text);
      });
      return cards;
    });
    const hasKeywords = keywordCards.length > 0;
    report('Test 1', 'Keyword cards with real data', hasKeywords, `Keywords: ${keywordCards.join(' | ')}`);

    // Click first keyword card
    if (keywordCards.length > 0) {
      await page.locator('h3').first().click();
      await page.waitForTimeout(500);

      // Click START BRIEFING
      await page.evaluate(() => {
        const allBtns = document.querySelectorAll('button');
        for (const b of allBtns) {
          if (b.textContent.includes('START BRIEFING')) {
            b.click();
            break;
          }
        }
      });
      await page.waitForURL('**/matching**', { timeout: 10000 });

      const navigatedUrl = page.url();
      const navToMatching = navigatedUrl.includes('/matching');
      report('Test 1', 'Navigate to matching after START BRIEFING', navToMatching, `URL: ${navigatedUrl}`);
    }
  });

  // ==================== TEST 2: MATCHING PAGE - KEY INSIGHT ====================
  test('Test 2: Matching page KEY INSIGHT fix', async () => {
    await page.waitForTimeout(3000);
    await page.waitForLoadState('networkidle');

    await page.screenshot({ path: 'e2e/screenshots/t2-matching.png', fullPage: true });

    // Wait for MATCHING COMPLETED
    await expect(page.locator('text=MATCHING COMPLETED')).toBeVisible({ timeout: 15000 });

    const matchingData = await page.evaluate(() => {
      // KEY INSIGHT text
      let keyInsight = '';
      const allH3s = document.querySelectorAll('h3');
      allH3s.forEach(h3 => {
        if (h3.textContent.includes('KEY INSIGHT')) {
          const parent = h3.parentElement;
          const p = parent?.querySelector('p');
          keyInsight = p?.textContent?.trim() || '';
        }
      });

      // Logo info
      const logo = document.querySelector('h1');
      const logoText = logo?.textContent?.trim() || '';
      const logoClasses = logo?.getAttribute('class') || '';
      const logoClickable = logoClasses.includes('cursor-pointer');

      // Theme toggle (sun/moon)
      const buttons = document.querySelectorAll('button');
      let hasThemeToggle = false;
      buttons.forEach(b => {
        const text = b.textContent.trim();
        if (text === '☀️' || text === '🌙') hasThemeToggle = true;
      });

      return { keyInsight, logoText, logoClickable, hasThemeToggle };
    });

    // CHECK: KEY INSIGHT has TEXT content (NOT empty)
    const hasKeyInsight = matchingData.keyInsight.length > 10;
    report('Test 2', 'KEY INSIGHT has text content', hasKeyInsight, `Text: "${matchingData.keyInsight.substring(0, 200)}"`);

    // CHECK: Logo is clickable
    report('Test 2', 'Logo is clickable', matchingData.logoClickable, `Logo: "${matchingData.logoText}", classes include cursor-pointer: ${matchingData.logoClickable}`);

    // CHECK: Theme toggle present
    report('Test 2', 'Theme toggle (sun/moon) present', matchingData.hasThemeToggle, `Has toggle: ${matchingData.hasThemeToggle}`);

    // Click NEXT STEP
    await page.locator('button:has-text("NEXT STEP")').click();
    await page.waitForURL('**/story**', { timeout: 5000 });
    report('Test 2', 'Navigate to story', page.url().includes('/story'), `URL: ${page.url()}`);
  });

  // ==================== TEST 3: STORY PAGE ====================
  test('Test 3: Story page', async () => {
    await page.waitForTimeout(3000);
    await page.waitForLoadState('networkidle');

    await page.screenshot({ path: 'e2e/screenshots/t3-story.png', fullPage: true });

    const storyData = await page.evaluate(() => {
      // Logo
      const logo = document.querySelector('h1');
      const logoClasses = logo?.getAttribute('class') || '';
      const logoClickable = logoClasses.includes('cursor-pointer');

      // Story title
      const h2 = document.querySelector('main h2');
      const title = h2?.textContent?.trim() || '';

      // Story paragraphs
      const paragraphs = [];
      document.querySelectorAll('main p').forEach(p => {
        const t = p.textContent.trim();
        if (t.length > 20) paragraphs.push(t.substring(0, 200));
      });

      // Thinking Point
      let thinkingPointText = '';
      const body = document.body.textContent;
      const hasThinkingPoint = body.includes('Thinking Point');
      // Try to find the thinking point content
      document.querySelectorAll('h3, .font-semibold').forEach(el => {
        if (el.textContent.includes('Thinking Point')) {
          const parent = el.closest('div');
          const p = parent?.querySelector('p');
          thinkingPointText = p?.textContent?.trim() || 'Present but no text found';
        }
      });

      return { logoClickable, title, paragraphs, hasThinkingPoint, thinkingPointText };
    });

    // CHECK: Logo is clickable
    report('Test 3', 'Logo is clickable', storyData.logoClickable, `cursor-pointer: ${storyData.logoClickable}`);

    // CHECK: Story content present
    const hasContent = storyData.paragraphs.length > 0;
    report('Test 3', 'Story content present', hasContent, `Title: "${storyData.title}", Paragraphs: ${storyData.paragraphs.length}`);

    // CHECK: Thinking Point present with text
    report('Test 3', 'Thinking Point present', storyData.hasThinkingPoint, `Text: "${storyData.thinkingPointText.substring(0, 150)}"`);

    // Click NEXT STEP
    const nextBtn = page.locator('button:has-text("NEXT STEP")');
    if (await nextBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await nextBtn.click();
      await page.waitForURL('**/comparison**', { timeout: 5000 });
      report('Test 3', 'Navigate to comparison', page.url().includes('/comparison'), `URL: ${page.url()}`);
    } else {
      report('Test 3', 'Navigate to comparison', false, 'NEXT STEP button not found');
    }
  });

  // ==================== TEST 4: COMPARISON PAGE - REAL PER DATA ====================
  test('Test 4: Comparison page real PER data', async () => {
    await page.waitForTimeout(3000);
    await page.waitForLoadState('networkidle');

    await page.screenshot({ path: 'e2e/screenshots/t4-comparison.png', fullPage: true });

    const compData = await page.evaluate(() => {
      // Logo
      const logo = document.querySelector('h1');
      const logoClasses = logo?.getAttribute('class') || '';
      const logoClickable = logoClasses.includes('cursor-pointer');

      // PER values - look for "Nx" pattern
      const perValues = [];
      document.querySelectorAll('span').forEach(span => {
        const text = span.textContent.trim();
        if (text.match(/^\d+(\.\d+)?x$/)) perValues.push(text);
      });

      // Company names in PER chart
      const perCompanies = [];
      document.querySelectorAll('.card p.text-sm.font-semibold').forEach(p => {
        perCompanies.push(p.textContent.trim());
      });

      // Analysis paragraphs
      const analysis = [];
      document.querySelectorAll('main .space-y-4 p, main .space-y-8 p').forEach(p => {
        const text = p.textContent.trim();
        if (text.length > 20) analysis.push(text.substring(0, 300));
      });

      // Check for generic template text
      const bodyText = document.body.textContent;
      const hasGenericText = bodyText.includes('[시장 상황]') || bodyText.includes('[분석 텍스트]');

      // Poll question
      let pollQuestion = '';
      // Look for the poll section
      const allEls = document.querySelectorAll('p, h3, h4');
      allEls.forEach(el => {
        const text = el.textContent.trim();
        if (text.includes('?') && text.length > 10 && text.length < 200) {
          if (!pollQuestion) pollQuestion = text;
        }
      });

      // Check if poll is generic
      const genericPoll = pollQuestion === 'What do you think?' || pollQuestion === '';

      return {
        logoClickable, perValues, perCompanies, analysis,
        hasGenericText, pollQuestion, genericPoll,
        bodySnippet: bodyText.substring(0, 3000)
      };
    });

    // CHECK: PER values are NON-ZERO
    const perNonZero = compData.perValues.length >= 2 && !compData.perValues.every(v => v === '0x');
    report('Test 4', 'PER values NON-ZERO', perNonZero, `PER values: ${compData.perValues.join(' vs ')}`);

    // CHECK: Company names in PER chart (NOT just "Past"/"Present")
    const hasRealCompanyNames = compData.perCompanies.length >= 2 &&
      !compData.perCompanies.every(n => n === 'Past' || n === 'Present' || n === 'Past ()' || n === 'Present ()');
    report('Test 4', 'Company names in PER chart', hasRealCompanyNames, `Companies: ${compData.perCompanies.join(' vs ')}`);

    // CHECK: Analysis text is present (NOT generic template)
    const hasRealAnalysis = compData.analysis.length > 0 && !compData.hasGenericText;
    report('Test 4', 'Analysis text present (not generic)', hasRealAnalysis, `Paragraphs: ${compData.analysis.length}, Text: "${(compData.analysis[0] || 'NONE').substring(0, 200)}"`);

    // CHECK: Poll question is specific (NOT generic)
    report('Test 4', 'Poll question specific', !compData.genericPoll, `Question: "${compData.pollQuestion}"`);

    // CHECK: Logo clickable
    report('Test 4', 'Logo is clickable', compData.logoClickable, `cursor-pointer: ${compData.logoClickable}`);

    // Click NEXT STEP
    const nextBtn = page.locator('button:has-text("NEXT STEP")');
    if (await nextBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await nextBtn.click();
      await page.waitForURL('**/companies**', { timeout: 5000 });
      report('Test 4', 'Navigate to companies', page.url().includes('/companies'), `URL: ${page.url()}`);
    } else {
      report('Test 4', 'Navigate to companies', false, 'NEXT STEP button not found');
    }
  });

  // ==================== TEST 5: COMPANIES PAGE - NO DUPLICATE TEXT ====================
  test('Test 5: Companies page no duplicate text', async () => {
    await page.waitForTimeout(3000);
    await page.waitForLoadState('networkidle');

    await page.screenshot({ path: 'e2e/screenshots/t5-companies.png', fullPage: true });

    const companiesData = await page.evaluate(() => {
      // Logo
      const logo = document.querySelector('h1');
      const logoClasses = logo?.getAttribute('class') || '';
      const logoClickable = logoClasses.includes('cursor-pointer');

      // Company cards
      const companies = [];
      document.querySelectorAll('.space-y-4 > div').forEach(card => {
        const name = card.querySelector('h3')?.textContent?.trim() || '';
        const code = card.querySelector('.text-sm.text-text-secondary')?.textContent?.trim() || '';
        const badge = card.querySelector('.badge')?.textContent?.trim() || '';
        const descEl = card.querySelector('p.text-sm.text-text-secondary');
        const desc = descEl?.textContent?.trim() || '';
        const detailEl = card.querySelector('p.text-sm.text-text-primary');
        const detail = detailEl?.textContent?.trim() || '';

        if (name) companies.push({ name, code, badge, desc, detail });
      });

      return { logoClickable, companies };
    });

    // CHECK: Leader company does NOT show same text in description AND detail
    let duplicateTextFound = false;
    let leaderInfo = '';
    for (const c of companiesData.companies) {
      if (c.badge === '대장주') {
        leaderInfo = `${c.name} - desc: "${c.desc.substring(0, 80)}", detail: "${c.detail.substring(0, 80)}"`;
        if (c.desc && c.detail && c.desc === c.detail) {
          duplicateTextFound = true;
        }
      }
    }
    report('Test 5', 'Leader NO duplicate text in desc/detail', !duplicateTextFound, leaderInfo || 'No leader found');

    // CHECK: Logo clickable
    report('Test 5', 'Logo is clickable', companiesData.logoClickable, `cursor-pointer: ${companiesData.logoClickable}`);

    // CHECK: Company names and role badges
    const hasCompanies = companiesData.companies.length > 0;
    const companySummary = companiesData.companies.map(c => `${c.name} [${c.badge}]`).join(', ');
    report('Test 5', 'Company names and role badges displayed', hasCompanies, companySummary);
  });

  // ==================== TEST 6: LOGO NAVIGATION TEST ====================
  test('Test 6: Logo navigation test', async () => {
    // On Companies page, click "History Mirror" logo
    const logoEl = page.locator('h1:has-text("History Mirror")');
    const isLogoVisible = await logoEl.isVisible().catch(() => false);

    if (isLogoVisible) {
      // Try clicking the logo
      try {
        await logoEl.click();
        await page.waitForTimeout(2000);
      } catch (e) {
        // If click fails, try evaluate
        await page.evaluate(() => {
          const h1 = document.querySelector('h1');
          if (h1) h1.click();
        });
        await page.waitForTimeout(2000);
      }

      const currentUrl = page.url();
      const isHome = currentUrl.endsWith('/') || currentUrl.endsWith(':3001') || currentUrl === 'http://localhost:3001/';
      report('Test 6', 'Logo click navigates to home', isHome, `URL after logo click: ${currentUrl}`);

      await page.screenshot({ path: 'e2e/screenshots/t6-logo-nav.png', fullPage: true });
    } else {
      report('Test 6', 'Logo click navigates to home', false, 'Logo not visible on Companies page');
    }
  });

  // ==================== TEST 7: HISTORY PAGE NAVBAR ====================
  test('Test 7: History page navbar', async () => {
    await page.goto('/history');
    await page.waitForTimeout(2000);
    await page.waitForLoadState('networkidle');

    await page.screenshot({ path: 'e2e/screenshots/t7-history.png', fullPage: true });

    const navData = await page.evaluate(() => {
      const nav = document.querySelector('nav');
      const buttons = nav ? nav.querySelectorAll('button') : [];
      const tabTexts = [];
      buttons.forEach(b => tabTexts.push(b.textContent.trim()));
      return { tabTexts };
    });

    const has홈 = navData.tabTexts.some(t => t.includes('홈'));
    const has히스토리 = navData.tabTexts.some(t => t.includes('히스토리'));
    const has검색 = navData.tabTexts.some(t => t.includes('검색'));
    const has프로필 = navData.tabTexts.some(t => t.includes('프로필'));
    const onlyTwoTabs = has홈 && has히스토리 && !has검색 && !has프로필;

    report('Test 7', 'Bottom nav ONLY 2 tabs (홈+히스토리)', onlyTwoTabs,
      `Tabs: ${navData.tabTexts.join(', ')} | 검색: ${has검색}, 프로필: ${has프로필}`);
  });
});
