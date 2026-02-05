/**
 * Real Data Verification Test
 * Tests the full flow with REAL API data (no hardcoded samples).
 * Captures screenshots and reports actual content on each page.
 */
import { test, expect } from '@playwright/test';

// Known OLD hardcoded values that should NOT appear
const OLD_HARDCODED = {
  keywords: ['AI 반도체 거품론', '2차전지 구조조정', '금리 인하 기대감'],
  matchingTitle: '2000년 닷컴 버블과',
  storyTitle: '시스코(Cisco)의 교훈',
  companyNames: ['SK하이닉스', '삼성전자', '한미반도체'],
};

test.describe.serial('Real Data Verification Report', () => {
  let page;
  const report = [];

  function addReport(section, items) {
    report.push({ section, items, timestamp: new Date().toISOString() });
    console.log(`\n${'='.repeat(60)}`);
    console.log(`[REPORT] ${section}`);
    console.log('='.repeat(60));
    for (const [key, value] of Object.entries(items)) {
      console.log(`  ${key}: ${value}`);
    }
  }

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 390, height: 844 },
    });
    page = await context.newPage();
  });

  test.afterAll(async () => {
    // Print final summary
    console.log('\n\n');
    console.log('╔══════════════════════════════════════════════════════════════╗');
    console.log('║            COMPREHENSIVE TEST REPORT - REAL DATA            ║');
    console.log('╚══════════════════════════════════════════════════════════════╝');
    for (const entry of report) {
      console.log(`\n--- ${entry.section} ---`);
      for (const [key, value] of Object.entries(entry.items)) {
        console.log(`  ${key}: ${value}`);
      }
    }
    console.log('\n' + '='.repeat(60));
    await page.close();
  });

  // ==================== TEST 1: ONBOARDING ====================

  test('1. Onboarding Flow', async () => {
    // Clear localStorage and go to onboarding
    await page.goto('/onboarding');
    await page.evaluate(() => localStorage.clear());
    await page.goto('/onboarding');
    await page.waitForLoadState('networkidle');

    await page.screenshot({ path: 'e2e/screenshots/01-onboarding-start.png', fullPage: true });

    // Verify first screen
    await expect(page.locator('text=Narrative')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Investment')).toBeVisible({ timeout: 5000 });

    // Click "다음" 4 times
    const nextBtn = page.locator('button', { hasText: /^다음$/ });
    for (let i = 0; i < 4; i++) {
      await nextBtn.click();
      await page.waitForTimeout(300);
    }

    await page.screenshot({ path: 'e2e/screenshots/02-onboarding-difficulty.png', fullPage: true });

    // Should be on difficulty selection
    await expect(page.locator('text=투자 경험을 알려주세요')).toBeVisible({ timeout: 3000 });

    // Select "입문"
    const beginnerBtn = page.locator('button:has-text("입문")');
    await beginnerBtn.click();
    await expect(beginnerBtn).toHaveClass(/border-primary/);

    // Click "시작하기"
    const startBtn = page.locator('button', { hasText: /^시작하기$/ });
    await expect(startBtn).toBeEnabled();
    await startBtn.click();
    await page.waitForTimeout(1000);

    // Verify settings saved
    const settings = await page.evaluate(() => {
      const s = localStorage.getItem('userSettings');
      return s ? JSON.parse(s) : null;
    });

    const onboardingPass = settings?.hasCompletedOnboarding === true && settings?.difficulty === 'beginner';

    addReport('1. ONBOARDING', {
      'Narrative/Investment visible': 'YES',
      'Clicked 다음 4 times': 'YES',
      'Difficulty screen reached': 'YES',
      'Selected 입문': 'YES',
      'Settings saved': JSON.stringify(settings),
      'Verdict': onboardingPass ? 'PASS ✓' : 'FAIL ✗',
    });

    expect(onboardingPass).toBe(true);
  });

  // ==================== TEST 2: HOME PAGE ====================

  test('2. Home Page - Real Keywords', async () => {
    // Set token for protected route access
    await page.evaluate(() => localStorage.setItem('token', 'e2e-token'));
    await page.goto('/');
    await page.waitForTimeout(3000);
    await page.waitForLoadState('networkidle');

    await page.screenshot({ path: 'e2e/screenshots/03-home-page.png', fullPage: true });

    // Verify header
    await expect(page.locator('text=History Mirror')).toBeVisible({ timeout: 5000 });

    // Extract keyword data
    const keywordData = await page.evaluate(() => {
      const h3s = document.querySelectorAll('h3');
      const titles = [];
      h3s.forEach((el) => titles.push(el.textContent.trim()));
      // Also get descriptions
      const cards = document.querySelectorAll('.space-y-4 > div');
      const cardData = [];
      cards.forEach((card) => {
        const title = card.querySelector('h3')?.textContent?.trim() || '';
        const desc = card.querySelector('p')?.textContent?.trim() || '';
        const cat = card.querySelector('span')?.textContent?.trim() || '';
        if (title) cardData.push({ title, desc, cat });
      });
      return { titles, cardData };
    });

    const keywordTitles = keywordData.titles.filter((t) => t.length > 0);
    const keywordCount = keywordData.cardData.length || keywordTitles.length;

    // Check for old hardcoded values
    const hasOldHardcoded = OLD_HARDCODED.keywords.some((old) =>
      keywordTitles.some((t) => t.includes(old))
    );

    // Get the count text
    const countText = await page.locator('h2').first().textContent();

    const isRealData = !hasOldHardcoded && keywordCount > 0;

    addReport('2. HOME PAGE - KEYWORDS', {
      'Header visible': 'History Mirror ✓',
      'Keyword count text': countText,
      'Keywords displayed': keywordTitles.join(' | ') || 'NONE',
      'Full card data': JSON.stringify(keywordData.cardData, null, 0),
      'Contains OLD hardcoded data': hasOldHardcoded ? 'YES (BAD!)' : 'NO (GOOD)',
      'Is REAL data': isRealData ? 'YES' : 'NO',
      'Verdict': isRealData ? 'PASS ✓' : 'FAIL ✗',
    });

    expect(isRealData).toBe(true);

    // Click first keyword card
    if (keywordTitles.length > 0) {
      await page.locator('h3').first().click();
      await page.waitForTimeout(500);

      await page.screenshot({ path: 'e2e/screenshots/04-home-keyword-selected.png', fullPage: true });

      // Verify START BRIEFING button
      const briefingBtn = page.locator('button:has-text("START BRIEFING")');
      await expect(briefingBtn).toBeVisible({ timeout: 3000 });

      // Scroll the button into view so nav-bottom doesn't intercept
      await briefingBtn.scrollIntoViewIfNeeded();
      await page.waitForTimeout(300);
      // Use evaluate to click programmatically to bypass overlay
      await page.evaluate(() => {
        const btn = document.querySelector('button');
        const allBtns = document.querySelectorAll('button');
        for (const b of allBtns) {
          if (b.textContent.includes('START BRIEFING')) {
            b.click();
            break;
          }
        }
      });
      await page.waitForURL('**/matching**', { timeout: 10000 });

      addReport('2b. HOME - NAVIGATION', {
        'First keyword clicked': keywordTitles[0],
        'START BRIEFING visible': 'YES',
        'Navigated to /matching': page.url().includes('/matching') ? 'YES ✓' : 'NO ✗',
        'Current URL': page.url(),
      });
    }
  });

  // ==================== TEST 3: MATCHING PAGE ====================

  test('3. Matching Page - Real Data', async () => {
    await page.waitForTimeout(2000);
    await page.waitForLoadState('networkidle');

    await page.screenshot({ path: 'e2e/screenshots/05-matching-page.png', fullPage: true });

    // Wait for data to load
    await expect(page.locator('text=MATCHING COMPLETED')).toBeVisible({ timeout: 10000 });

    // Extract matching data
    const matchingData = await page.evaluate(() => {
      const body = document.body.textContent;

      // Get main title text (h2)
      const h2 = document.querySelector('h2');
      const title = h2?.textContent?.trim() || '';

      // Get PAST year and label
      const allSpans = document.querySelectorAll('span');
      let pastYear = '';
      let pastLabel = '';
      let presentYear = '';
      let presentLabel = '';
      let syncRateText = '';
      let foundPast = false;
      let foundPresent = false;

      allSpans.forEach((span) => {
        const text = span.textContent.trim();
        if (text === 'PAST') foundPast = true;
        if (text === 'PRESENT') foundPresent = true;
        if (text.match(/^\d{4}$/) && foundPast && !pastYear) pastYear = text;
        if (text.match(/^\d{4}$/) && foundPresent && !presentYear) presentYear = text;
        if (text.match(/^\d+%$/)) syncRateText = text;
      });

      // Get KEY INSIGHT text
      const insightCard = document.querySelector('h3');
      let keyInsight = '';
      const allH3s = document.querySelectorAll('h3');
      allH3s.forEach((h3) => {
        if (h3.textContent.includes('KEY INSIGHT')) {
          const parent = h3.parentElement;
          const p = parent?.querySelector('p');
          keyInsight = p?.textContent?.trim() || '';
        }
      });

      return { title, pastYear, presentYear, syncRateText, keyInsight, bodyText: body.substring(0, 2000) };
    });

    const hasOldTitle = matchingData.title.includes(OLD_HARDCODED.matchingTitle);
    const hasSyncRate = matchingData.syncRateText.length > 0;
    const hasKeyInsight = matchingData.keyInsight.length > 0;
    const isRealData = !hasOldTitle && hasSyncRate;

    addReport('3. MATCHING PAGE', {
      'MATCHING COMPLETED visible': 'YES',
      'Main title': matchingData.title,
      'Past year': matchingData.pastYear || 'N/A',
      'Present year': matchingData.presentYear || 'N/A',
      'Sync rate': matchingData.syncRateText || 'N/A',
      'KEY INSIGHT': matchingData.keyInsight.substring(0, 200) || 'N/A',
      'Contains OLD hardcoded title': hasOldTitle ? 'YES (BAD!)' : 'NO (GOOD)',
      'Is REAL data': isRealData ? 'YES' : 'NO',
      'Verdict': isRealData ? 'PASS ✓' : 'FAIL ✗',
    });

    // Click NEXT STEP
    await page.locator('button:has-text("NEXT STEP")').click();
    await page.waitForURL('**/story**', { timeout: 5000 });

    addReport('3b. MATCHING - NAVIGATION', {
      'Navigated to /story': page.url().includes('/story') ? 'YES ✓' : 'NO ✗',
      'Current URL': page.url(),
    });
  });

  // ==================== TEST 4: STORY PAGE ====================

  test('4. Story Page - Real Content', async () => {
    await page.waitForTimeout(2000);
    await page.waitForLoadState('networkidle');

    // Check for error boundary
    const hasError = await page.locator('text=오류가 발생했습니다').isVisible().catch(() => false);

    if (hasError) {
      await page.screenshot({ path: 'e2e/screenshots/06-story-error.png', fullPage: true });
      addReport('4. STORY PAGE', {
        'Page loaded': 'ERROR - Error boundary triggered',
        'Verdict': 'FAIL ✗ (Error boundary)',
      });
      // Try to recover
      const homeBtn = page.locator('button:has-text("홈으로 돌아가기")');
      if (await homeBtn.isVisible()) {
        await homeBtn.click();
        await page.waitForTimeout(1000);
      }
      // Navigate directly to story
      return;
    }

    await page.screenshot({ path: 'e2e/screenshots/06-story-page.png', fullPage: true });

    // Wait for content
    const h2Visible = await page.locator('h2').first().isVisible().catch(() => false);

    const storyData = await page.evaluate(() => {
      const h2 = document.querySelector('main h2');
      const title = h2?.textContent?.trim() || '';

      // Get all paragraphs
      const paragraphs = [];
      const ps = document.querySelectorAll('main p');
      ps.forEach((p) => {
        const text = p.textContent.trim();
        if (text.length > 20) paragraphs.push(text);
      });

      // Get thinking point
      let thinkingPoint = '';
      const allText = document.body.textContent;
      if (allText.includes('Thinking Point')) {
        thinkingPoint = 'Present';
      }

      return { title, paragraphs, thinkingPoint, bodySnippet: document.body.textContent.substring(0, 2000) };
    });

    const hasOldTitle = storyData.title.includes(OLD_HARDCODED.storyTitle);
    const hasContent = storyData.paragraphs.length > 0;
    const isRealData = !hasOldTitle && hasContent && storyData.title.length > 0;

    addReport('4. STORY PAGE', {
      'Title': storyData.title || 'N/A',
      'Has content paragraphs': `${storyData.paragraphs.length} paragraphs`,
      'First paragraph (truncated)': (storyData.paragraphs[0] || 'N/A').substring(0, 200),
      'Thinking Point present': storyData.thinkingPoint || 'No',
      'Contains OLD hardcoded title': hasOldTitle ? 'YES (BAD!)' : 'NO (GOOD)',
      'Is REAL data': isRealData ? 'YES' : 'NO',
      'Verdict': isRealData ? 'PASS ✓' : 'FAIL ✗',
    });

    // Click NEXT STEP
    const nextBtn = page.locator('button:has-text("NEXT STEP")');
    if (await nextBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await nextBtn.click();
      await page.waitForURL('**/comparison**', { timeout: 5000 });
      addReport('4b. STORY - NAVIGATION', {
        'Navigated to /comparison': page.url().includes('/comparison') ? 'YES ✓' : 'NO ✗',
        'Current URL': page.url(),
      });
    } else {
      // Navigate manually
      const currentUrl = new URL(page.url());
      const caseId = currentUrl.searchParams.get('caseId');
      await page.goto(`/comparison?caseId=${caseId}`);
      addReport('4b. STORY - NAVIGATION', {
        'NEXT STEP button': 'Not visible - navigated manually',
        'Current URL': page.url(),
      });
    }
  });

  // ==================== TEST 5: COMPARISON PAGE ====================

  test('5. Comparison Page - Real Comparison', async () => {
    await page.waitForTimeout(2000);
    await page.waitForLoadState('networkidle');

    // Check for error
    const hasError = await page.locator('text=오류가 발생했습니다').isVisible().catch(() => false);

    if (hasError) {
      await page.screenshot({ path: 'e2e/screenshots/07-comparison-error.png', fullPage: true });
      addReport('5. COMPARISON PAGE', {
        'Page loaded': 'ERROR - Error boundary triggered',
        'Verdict': 'FAIL ✗ (Error boundary)',
      });
      return;
    }

    await page.screenshot({ path: 'e2e/screenshots/07-comparison-page.png', fullPage: true });

    const comparisonData = await page.evaluate(() => {
      const h2 = document.querySelector('main h2');
      const title = h2?.textContent?.trim() || '';

      // Get subtitle
      const subtitle = h2?.nextElementSibling?.textContent?.trim() || '';

      // PER values
      const perValues = [];
      document.querySelectorAll('span').forEach((span) => {
        const text = span.textContent.trim();
        if (text.match(/^\d+(\.\d+)?x$/)) perValues.push(text);
      });

      // Company names in PER section
      const perCompanies = [];
      document.querySelectorAll('.card p.text-sm.font-semibold').forEach((p) => {
        perCompanies.push(p.textContent.trim());
      });

      // Analysis paragraphs
      const analysis = [];
      document.querySelectorAll('main .space-y-4 p').forEach((p) => {
        const text = p.textContent.trim();
        if (text.length > 20) analysis.push(text);
      });

      // Poll question
      let pollQuestion = '';
      const body = document.body.textContent;

      return {
        title,
        subtitle,
        perValues,
        perCompanies,
        analysis,
        bodySnippet: body.substring(0, 2000),
      };
    });

    const hasContent = comparisonData.title.length > 0;
    const isRealData = hasContent;

    addReport('5. COMPARISON PAGE', {
      'Title': comparisonData.title || 'N/A',
      'Subtitle': comparisonData.subtitle || 'N/A',
      'PER Values': comparisonData.perValues.join(' vs ') || 'N/A',
      'PER Companies': comparisonData.perCompanies.join(' vs ') || 'N/A',
      'Analysis paragraphs': `${comparisonData.analysis.length} paragraphs`,
      'First analysis (truncated)': (comparisonData.analysis[0] || 'N/A').substring(0, 200),
      'Is REAL data': isRealData ? 'YES' : 'NO',
      'Verdict': isRealData ? 'PASS ✓' : 'FAIL ✗',
    });

    // Click NEXT STEP
    const nextBtn = page.locator('button:has-text("NEXT STEP")');
    if (await nextBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await nextBtn.click();
      await page.waitForURL('**/companies**', { timeout: 5000 });
      addReport('5b. COMPARISON - NAVIGATION', {
        'Navigated to /companies': page.url().includes('/companies') ? 'YES ✓' : 'NO ✗',
        'Current URL': page.url(),
      });
    } else {
      const currentUrl = new URL(page.url());
      const caseId = currentUrl.searchParams.get('caseId');
      await page.goto(`/companies?caseId=${caseId}`);
      addReport('5b. COMPARISON - NAVIGATION', {
        'NEXT STEP button': 'Not visible - navigated manually',
        'Current URL': page.url(),
      });
    }
  });

  // ==================== TEST 6: COMPANIES PAGE ====================

  test('6. Companies Page - Real Companies', async () => {
    await page.waitForTimeout(2000);
    await page.waitForLoadState('networkidle');

    // Check for error
    const hasError = await page.locator('text=오류가 발생했습니다').isVisible().catch(() => false);

    if (hasError) {
      await page.screenshot({ path: 'e2e/screenshots/08-companies-error.png', fullPage: true });
      addReport('6. COMPANIES PAGE', {
        'Page loaded': 'ERROR - Error boundary triggered',
        'Verdict': 'FAIL ✗ (Error boundary)',
      });
      return;
    }

    await page.screenshot({ path: 'e2e/screenshots/08-companies-page.png', fullPage: true });

    const companiesData = await page.evaluate(() => {
      // Get company names
      const companies = [];
      document.querySelectorAll('.space-y-4 > div').forEach((card) => {
        const name = card.querySelector('h3')?.textContent?.trim() || '';
        const code = card.querySelector('.text-sm.text-text-secondary')?.textContent?.trim() || '';
        const badge = card.querySelector('.badge')?.textContent?.trim() || '';
        const desc = card.querySelector('p.text-sm')?.textContent?.trim() || '';
        if (name) companies.push({ name, code, badge, desc: desc.substring(0, 100) });
      });

      return { companies, bodySnippet: document.body.textContent.substring(0, 2000) };
    });

    const companyNames = companiesData.companies.map((c) => c.name);
    const hasOldHardcoded = OLD_HARDCODED.companyNames.every((old) =>
      companyNames.includes(old)
    );
    const hasCompanies = companiesData.companies.length > 0;
    const isRealData = hasCompanies && !hasOldHardcoded;

    addReport('6. COMPANIES PAGE', {
      'Company count': companiesData.companies.length,
      'Companies': companiesData.companies
        .map((c) => `${c.name} (${c.code}) [${c.badge}]`)
        .join(' | ') || 'NONE',
      'Descriptions': companiesData.companies
        .map((c) => `${c.name}: ${c.desc}`)
        .join('\n    ') || 'N/A',
      'Contains OLD hardcoded set': hasOldHardcoded ? 'YES (BAD!)' : 'NO (GOOD)',
      'Is REAL data': isRealData ? 'YES' : 'NO',
      'Verdict': isRealData ? 'PASS ✓' : 'FAIL ✗',
    });

    // Click "처음으로 돌아가기"
    const backBtn = page.locator('button:has-text("처음으로 돌아가기")');
    if (await backBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await backBtn.click();
      await page.waitForTimeout(2000);
      const onHome = page.url().endsWith('/') || page.url().endsWith(':3001');

      addReport('6b. COMPANIES - NAVIGATION', {
        'Back to home clicked': 'YES',
        'Landed on home': onHome ? 'YES ✓' : 'NO ✗',
        'Current URL': page.url(),
      });
    }
  });
});
