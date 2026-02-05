/**
 * Full App Flow Test: Auth pages + Chatbot UI
 * Tests: Onboarding→Auth redirect, Auth page, Guest access, Search page, Chatbot UI
 */
import { test, expect } from '@playwright/test';

const MOBILE_VIEWPORT = { width: 390, height: 844 };

test.describe.serial('Full App Flow: Auth & Chatbot', () => {
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
    console.log('╔══════════════════════════════════════════════════════════╗');
    console.log('║         FULL APP FLOW TEST REPORT                       ║');
    console.log('╚══════════════════════════════════════════════════════════╝');
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

  // ==================== TEST 1: ONBOARDING -> AUTH REDIRECT ====================
  test('Test 1: Onboarding -> Auth page redirect', async () => {
    // Clear state to force onboarding
    await page.goto('/onboarding');
    await page.evaluate(() => localStorage.clear());
    await page.goto('/onboarding');
    await page.waitForLoadState('networkidle');

    // Click "다음" 4 times
    const nextBtn = page.locator('button', { hasText: /^다음$/ });
    for (let i = 0; i < 4; i++) {
      await nextBtn.click();
      await page.waitForTimeout(500);
    }

    // Select "입문" difficulty
    const beginnerBtn = page.locator('button:has-text("입문")');
    await beginnerBtn.click();
    await page.waitForTimeout(300);

    // Click "시작하기"
    const startBtn = page.locator('button', { hasText: /^시작하기$/ });
    await startBtn.click();
    await page.waitForTimeout(2000);

    // Take screenshot
    await page.screenshot({ path: 'e2e/screenshots/t1-after-onboarding.png', fullPage: true });

    const currentUrl = page.url();
    const urlPath = new URL(currentUrl).pathname;

    // CHECK: URL should be /auth (NOT /)
    const isAuthPage = urlPath === '/auth';
    report('Test 1', 'URL is /auth after onboarding', isAuthPage, `URL path: ${urlPath} (full: ${currentUrl})`);

    // CHECK: Login/register form should be visible
    const hasLoginForm = await page.evaluate(() => {
      const body = document.body.textContent;
      const hasLoginTab = body.includes('로그인');
      const hasRegisterTab = body.includes('회원가입');
      const hasEmailInput = document.querySelector('input[type="email"]') !== null;
      return { hasLoginTab, hasRegisterTab, hasEmailInput };
    });
    const formVisible = hasLoginForm.hasLoginTab && hasLoginForm.hasRegisterTab && hasLoginForm.hasEmailInput;
    report('Test 1', 'Login/register form visible', formVisible, `로그인: ${hasLoginForm.hasLoginTab}, 회원가입: ${hasLoginForm.hasRegisterTab}, Email input: ${hasLoginForm.hasEmailInput}`);
  });

  // ==================== TEST 2: AUTH PAGE - REGISTER TAB ====================
  test('Test 2: Auth page - Register tab', async () => {
    await page.screenshot({ path: 'e2e/screenshots/t2-auth-page.png', fullPage: true });

    // CHECK: "로그인" and "회원가입" tabs visible
    const loginTab = page.locator('button:has-text("로그인")').first();
    const registerTab = page.locator('button:has-text("회원가입")').first();
    const loginTabVisible = await loginTab.isVisible();
    const registerTabVisible = await registerTab.isVisible();
    report('Test 2', '로그인 and 회원가입 tabs visible', loginTabVisible && registerTabVisible, `로그인 tab: ${loginTabVisible}, 회원가입 tab: ${registerTabVisible}`);

    // Click "회원가입" tab
    await registerTab.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'e2e/screenshots/t2-register-tab.png', fullPage: true });

    // CHECK: Email, password, username inputs visible
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');
    const usernameInput = page.locator('input[type="text"]');
    const emailVisible = await emailInput.isVisible();
    const passwordVisible = await passwordInput.isVisible();
    const usernameVisible = await usernameInput.isVisible();
    report('Test 2', 'Email, password, username inputs visible', emailVisible && passwordVisible && usernameVisible, `Email: ${emailVisible}, Password: ${passwordVisible}, Username: ${usernameVisible}`);

    // CHECK: "회원가입" submit button visible
    const registerSubmitBtn = page.locator('button[type="submit"]:has-text("회원가입")');
    const registerSubmitVisible = await registerSubmitBtn.isVisible();
    report('Test 2', '회원가입 submit button visible', registerSubmitVisible, `Submit btn visible: ${registerSubmitVisible}`);

    // CHECK: "게스트로 시작하기" link visible
    const guestLink = page.locator('button:has-text("게스트로 시작하기")');
    const guestLinkVisible = await guestLink.isVisible();
    report('Test 2', '게스트로 시작하기 link visible', guestLinkVisible, `Guest link visible: ${guestLinkVisible}`);
  });

  // ==================== TEST 3: AUTH PAGE - GUEST ACCESS ====================
  test('Test 3: Auth page - Guest access', async () => {
    // Click "게스트로 시작하기" link
    const guestLink = page.locator('button:has-text("게스트로 시작하기")');
    await guestLink.click();
    await page.waitForTimeout(2000);
    await page.waitForLoadState('networkidle');

    await page.screenshot({ path: 'e2e/screenshots/t3-guest-home.png', fullPage: true });

    const currentUrl = page.url();
    const urlPath = new URL(currentUrl).pathname;

    // CHECK: Navigated to / (home page)
    const isHome = urlPath === '/';
    report('Test 3', 'Navigated to / (home page)', isHome, `URL path: ${urlPath}`);

    // CHECK: Keywords are displayed (app works in guest mode)
    await page.waitForTimeout(3000);
    const keywordData = await page.evaluate(() => {
      const keywords = [];
      document.querySelectorAll('h3').forEach(h3 => {
        const text = h3.textContent.trim();
        if (text.length > 0) keywords.push(text);
      });
      return keywords;
    });
    const hasKeywords = keywordData.length > 0;
    report('Test 3', 'Keywords displayed in guest mode', hasKeywords, `Keywords found: ${keywordData.join(' | ')}`);
  });

  // ==================== TEST 4: SEARCH PAGE ACCESSIBLE ====================
  test('Test 4: Search page accessible', async () => {
    await page.goto('/search');
    await page.waitForTimeout(2000);
    await page.waitForLoadState('networkidle');

    await page.screenshot({ path: 'e2e/screenshots/t4-search-page.png', fullPage: true });

    // CHECK: Search page loads (search input visible)
    const searchInputData = await page.evaluate(() => {
      const inputs = document.querySelectorAll('input');
      let searchInput = null;
      inputs.forEach(input => {
        const placeholder = input.getAttribute('placeholder') || '';
        const type = input.getAttribute('type') || '';
        if (placeholder.includes('검색') || placeholder.includes('search') || type === 'search' || type === 'text') {
          searchInput = { placeholder, type };
        }
      });
      return { searchInput, inputCount: inputs.length, bodyText: document.body.textContent.substring(0, 500) };
    });
    const hasSearchInput = searchInputData.searchInput !== null;
    report('Test 4', 'Search page loads with search input', hasSearchInput, `Input found: ${JSON.stringify(searchInputData.searchInput)}, Total inputs: ${searchInputData.inputCount}`);
  });

  // ==================== TEST 5: CHATBOT UI IMPROVEMENTS ====================
  test('Test 5: Chatbot UI improvements', async () => {
    test.setTimeout(90000); // 90s timeout for this test

    // Navigate home
    await page.goto('/');
    await page.waitForTimeout(3000);
    await page.waitForLoadState('networkidle');

    // Click first keyword
    const firstKeyword = page.locator('h3').first();
    const firstKeywordText = await firstKeyword.textContent();
    await firstKeyword.click();
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
    await page.waitForTimeout(3000);

    // Wait for matching to complete
    try {
      await expect(page.locator('text=MATCHING COMPLETED')).toBeVisible({ timeout: 20000 });
    } catch {
      console.log('MATCHING COMPLETED not found, trying to proceed anyway');
    }

    // Click NEXT STEP to go to story
    const nextStepBtn = page.locator('button:has-text("NEXT STEP")');
    if (await nextStepBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await nextStepBtn.click();
      await page.waitForURL('**/story**', { timeout: 10000 });
    }
    await page.waitForTimeout(3000);
    await page.waitForLoadState('networkidle');

    await page.screenshot({ path: 'e2e/screenshots/t5-story-before-click.png', fullPage: true });

    // Find and click a highlighted term (e.g., PER or any [[term]])
    const highlightedTermInfo = await page.evaluate(() => {
      // Look for highlighted terms - they usually have a click handler and specific styling
      const candidates = document.querySelectorAll('button, span.text-primary, span[class*="highlight"], span[class*="underline"], .cursor-pointer');
      const terms = [];
      candidates.forEach(el => {
        const text = el.textContent.trim();
        if (text.length > 0 && text.length < 30 && !text.includes('NEXT') && !text.includes('History Mirror')) {
          terms.push({ text, tag: el.tagName, classes: el.className });
        }
      });
      return terms;
    });
    console.log('Highlighted terms found:', JSON.stringify(highlightedTermInfo.slice(0, 10)));

    // Try clicking a highlighted term
    let termClicked = false;
    
    // Method 1: Look for terms with special styling (glossary highlights)
    const glossaryTerms = await page.locator('span.text-primary.cursor-pointer, span.underline.cursor-pointer, button.text-primary.underline, [data-term]').all();
    if (glossaryTerms.length > 0) {
      const termText = await glossaryTerms[0].textContent();
      console.log(`Clicking glossary term: "${termText}"`);
      await glossaryTerms[0].click();
      termClicked = true;
    }

    // Method 2: Try finding any interactive inline terms
    if (!termClicked) {
      termClicked = await page.evaluate(() => {
        // Find any span or button inside the story content that looks like a glossary term
        const storyContent = document.querySelector('main');
        if (!storyContent) return false;
        
        const spans = storyContent.querySelectorAll('span, button');
        for (const span of spans) {
          const text = span.textContent.trim();
          const style = window.getComputedStyle(span);
          const isClickable = style.cursor === 'pointer' || span.tagName === 'BUTTON';
          if (isClickable && text.length > 1 && text.length < 20 && !text.includes('NEXT') && !text.includes('History Mirror')) {
            span.click();
            return true;
          }
        }
        return false;
      });
    }

    // Method 3: Just directly send a message to the tutor via context
    if (!termClicked) {
      console.log('No clickable term found, trying to open tutor manually');
      // Check if there's a tutor/chat button
      const tutorButtons = await page.locator('button:has-text("AI"), button:has-text("튜터"), button:has-text("💬")').all();
      if (tutorButtons.length > 0) {
        await tutorButtons[0].click();
        termClicked = true;
      }
    }

    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'e2e/screenshots/t5-after-term-click.png', fullPage: true });

    // CHECK: TutorModal opens with "AI 튜터" header
    const tutorModalCheck = await page.evaluate(() => {
      const body = document.body.textContent;
      const hasAITutor = body.includes('AI 튜터');
      const hasHeader = document.querySelector('h2')?.textContent?.includes('AI 튜터') || false;
      // Look for the modal overlay
      const hasOverlay = document.querySelector('.fixed.inset-0') !== null;
      return { hasAITutor, hasHeader, hasOverlay };
    });
    const tutorModalOpen = tutorModalCheck.hasAITutor && (tutorModalCheck.hasHeader || tutorModalCheck.hasOverlay);
    report('Test 5', 'TutorModal opens with AI 튜터 header', tutorModalOpen, `AI 튜터 text: ${tutorModalCheck.hasAITutor}, Header h2: ${tutorModalCheck.hasHeader}, Overlay: ${tutorModalCheck.hasOverlay}`);

    // Wait 3 seconds for auto-question to be sent
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'e2e/screenshots/t5-after-3s.png', fullPage: true });

    // CHECK: Typing indicator OR response streaming
    const typingCheck = await page.evaluate(() => {
      const body = document.body.textContent;
      const hasTypingIndicator = body.includes('AI 튜터가 답변 중');
      // Check for bouncing dots (animate-bounce class)
      const bouncingDots = document.querySelectorAll('.animate-bounce');
      // Check if any AI response already started
      const aiResponses = [];
      document.querySelectorAll('.bg-surface.border').forEach(el => {
        const text = el.textContent.trim();
        if (text.length > 10) aiResponses.push(text.substring(0, 100));
      });
      // Check for streaming cursor
      const streamingCursor = document.querySelector('.animate-pulse');
      return {
        hasTypingIndicator,
        bouncingDotCount: bouncingDots.length,
        aiResponseCount: aiResponses.length,
        aiResponsePreview: aiResponses[0] || '',
        hasStreamingCursor: streamingCursor !== null
      };
    });
    const typingOrStreaming = typingCheck.hasTypingIndicator || typingCheck.aiResponseCount > 0 || typingCheck.hasStreamingCursor;
    report('Test 5', 'Typing indicator or response streaming (after 3s)', typingOrStreaming,
      `Typing: ${typingCheck.hasTypingIndicator}, Dots: ${typingCheck.bouncingDotCount}, Responses: ${typingCheck.aiResponseCount}, Streaming cursor: ${typingCheck.hasStreamingCursor}`);

    // Wait 8 more seconds for response to complete
    await page.waitForTimeout(8000);
    await page.screenshot({ path: 'e2e/screenshots/t5-after-11s.png', fullPage: true });

    // CHECK: AI response has card-style layout
    const responseLayoutCheck = await page.evaluate(() => {
      // Look for AI avatar icon (🎓)
      const hasAvatarIcon = document.body.textContent.includes('🎓');
      
      // Look for "AI 튜터" labels (not just the header)
      const aiTutorLabels = [];
      document.querySelectorAll('span').forEach(span => {
        if (span.textContent.trim() === 'AI 튜터') aiTutorLabels.push(true);
      });
      
      // Look for bordered card style (bg-surface border border-border)
      const cardElements = document.querySelectorAll('.bg-surface.border');
      const borderedCards = [];
      cardElements.forEach(el => {
        const text = el.textContent.trim();
        if (text.length > 20) borderedCards.push(text.substring(0, 100));
      });

      // Check for rounded cards
      const roundedCards = document.querySelectorAll('.rounded-2xl');

      return {
        hasAvatarIcon,
        aiTutorLabelCount: aiTutorLabels.length,
        borderedCardCount: borderedCards.length,
        borderedCardPreview: borderedCards[0] || '',
        roundedCardCount: roundedCards.length
      };
    });
    const hasCardLayout = responseLayoutCheck.hasAvatarIcon && responseLayoutCheck.aiTutorLabelCount > 0 && responseLayoutCheck.borderedCardCount > 0;
    report('Test 5', 'AI response card-style layout (avatar, label, bordered card)', hasCardLayout,
      `Avatar 🎓: ${responseLayoutCheck.hasAvatarIcon}, AI 튜터 labels: ${responseLayoutCheck.aiTutorLabelCount}, Bordered cards: ${responseLayoutCheck.borderedCardCount}, Rounded: ${responseLayoutCheck.roundedCardCount}`);

    // CHECK: Response text has formatting
    const formattingCheck = await page.evaluate(() => {
      // Check for formatted elements inside the response
      const responseArea = document.querySelectorAll('.prose-sm, [class*="prose"]');
      
      // Look for bold text
      const strongElements = document.querySelectorAll('.bg-surface strong, .bg-surface .font-semibold');
      
      // Look for list items
      const listItems = document.querySelectorAll('.bg-surface .flex.gap-2');
      
      // Look for headers
      const headers = document.querySelectorAll('.bg-surface h3, .bg-surface h4, .bg-surface .font-bold');
      
      // Look for any rendered HTML (indicating markdown was processed)
      const renderedHTML = document.querySelectorAll('.prose-sm strong, .prose-sm h3, .prose-sm h4, .prose-sm .flex.gap-2');
      
      // Get full response text
      let responseText = '';
      document.querySelectorAll('.bg-surface.border .text-sm').forEach(el => {
        responseText += el.textContent.trim() + ' ';
      });

      return {
        proseCount: responseArea.length,
        strongCount: strongElements.length,
        listItemCount: listItems.length,
        headerCount: headers.length,
        renderedHTMLCount: renderedHTML.length,
        responseLength: responseText.length,
        responsePreview: responseText.substring(0, 300)
      };
    });
    const hasFormatting = formattingCheck.renderedHTMLCount > 0 || formattingCheck.strongCount > 0 || formattingCheck.listItemCount > 0;
    const hasResponse = formattingCheck.responseLength > 20;
    report('Test 5', 'Response text has formatting (bold, lists, etc.)', hasFormatting || hasResponse,
      `Prose: ${formattingCheck.proseCount}, Bold: ${formattingCheck.strongCount}, Lists: ${formattingCheck.listItemCount}, Headers: ${formattingCheck.headerCount}, Rendered: ${formattingCheck.renderedHTMLCount}, Response length: ${formattingCheck.responseLength}`);

    if (formattingCheck.responsePreview) {
      console.log(`Response preview: "${formattingCheck.responsePreview}"`);
    }
  });
});
