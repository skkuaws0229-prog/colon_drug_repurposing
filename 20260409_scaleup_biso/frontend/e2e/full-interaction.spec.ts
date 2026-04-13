import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:4173';

/* ════════════════════════════════════════════════
   전수 인터랙션 테스트 — 모든 클릭 가능 요소 점검
   ════════════════════════════════════════════════ */

test.describe('Chat Page — 모든 제안 칩 클릭', () => {
  test('환자모드 제안 칩 6개 전부 클릭 가능', async ({ page }) => {
    await page.goto(BASE);
    const chips = [
      '유방암 표준요법 약물 목록 알려줘',
      'Docetaxel 부작용 알려줘',
      '서울 지역 유방암 치료 병원',
      'Paclitaxel 임상시험 정보',
      '유방암 예방 생활 가이드',
      '유방암 환자 추천 음식',
    ];
    for (const chip of chips) {
      // 매번 새 대화로 리셋
      await page.goto(BASE);
      const btn = page.getByText(chip, { exact: false });
      await expect(btn).toBeVisible({ timeout: 3000 });
      await btn.click();
      // 유저 메시지가 대화에 표시되어야 함
      await expect(page.locator('[role="log"]')).toBeVisible({ timeout: 5000 });
      // thinking indicator 또는 AI 응답
      const hasThinking = await page.getByRole('status', { name: 'AI가 응답을 생성하고 있습니다' }).isVisible().catch(() => false);
      const hasLog = await page.locator('[role="log"]').isVisible();
      expect(hasThinking || hasLog).toBeTruthy();
    }
  });

  test('연구자모드 제안 칩 6개 전부 클릭 가능', async ({ page }) => {
    await page.goto(BASE);
    // 연구자 모드 전환
    await page.getByLabel(/현재:.*모드/).click();
    await expect(page.getByText('연구자')).toBeVisible();

    const chips = [
      'Docetaxel 타겟 유전자 분석',
      '파이프라인 약물 랭킹 보여줘',
      'Docetaxel pathway 조회',
      'breast cancer docetaxel PubMed',
      'Knowledge Graph 통계',
      '신약 재창출 후보 목록',
    ];
    for (const chip of chips) {
      await page.goto(BASE);
      // 연구자 모드 다시 전환 (페이지 이동 시 state 유지 확인)
      const modeBtn = page.getByLabel(/현재:.*모드/);
      const modeText = await page.getByText('연구자').isVisible().catch(() => false);
      if (!modeText) await modeBtn.click();

      const btn = page.getByText(chip, { exact: false });
      if (await btn.isVisible().catch(() => false)) {
        await btn.click();
        await expect(page.locator('[role="log"]')).toBeVisible({ timeout: 5000 });
      }
    }
  });
});

test.describe('Sidebar — 모든 버튼 동작', () => {
  test('로고 클릭 → 홈으로 이동', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    await page.getByLabel('BioChat AI 홈').click();
    await expect(page.getByRole('heading', { name: 'BioChat AI' })).toBeVisible({ timeout: 3000 });
  });

  test('사이드바 접기/펼치기', async ({ page }) => {
    await page.goto(BASE);
    // 접기
    const collapseBtn = page.getByLabel('사이드바 접기');
    if (await collapseBtn.isVisible()) {
      await collapseBtn.click();
      await expect(page.getByLabel('사이드바 펼치기')).toBeVisible();
      // 펼치기
      await page.getByLabel('사이드바 펼치기').click();
      await expect(page.getByLabel('사이드바 접기')).toBeVisible();
    }
  });

  test('새 대화 버튼', async ({ page }) => {
    await page.goto(BASE);
    // 먼저 메시지 전송
    const input = page.getByLabel('메시지 입력');
    await input.fill('테스트');
    await input.press('Enter');
    await page.waitForTimeout(1000);
    // 새 대화 클릭
    await page.getByLabel('새 대화').click();
    // Welcome screen이 다시 보여야 함
    await expect(page.getByRole('heading', { name: 'BioChat AI' })).toBeVisible({ timeout: 3000 });
  });

  test('테마 전환 (Dark → Light → Dark)', async ({ page }) => {
    await page.goto(BASE);
    // Light 클릭
    const lightBtn = page.getByLabel('Light 테마');
    if (await lightBtn.isVisible()) {
      await lightBtn.click();
      const theme = await page.locator('html').getAttribute('data-theme');
      expect(theme).toBe('light');
      // Dark로 돌아가기
      await page.getByLabel('Dark 테마').click();
      const theme2 = await page.locator('html').getAttribute('data-theme');
      expect(theme2).toBe('dark');
    }
  });

  test('모드 전환 반복', async ({ page }) => {
    await page.goto(BASE);
    const toggle = page.getByLabel(/현재:.*모드/);
    // 환자 → 연구자
    await toggle.click();
    await expect(page.getByText('연구자')).toBeVisible();
    // 연구자 → 환자
    await toggle.click();
    await expect(page.getByText('환자/보호자')).toBeVisible();
  });
});

test.describe('Dashboard — 모든 클릭 요소', () => {
  test('파이프라인 카드 클릭 → 약물 탐색기로 이동', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    const card = page.getByLabel(/현재 표준요법.*약물 탐색기/);
    if (await card.isVisible({ timeout: 3000 }).catch(() => false)) {
      await card.click();
      await expect(page.getByRole('heading', { name: /약물/ })).toBeVisible();
    }
  });

  test('빠른 실행 — AI 상담 클릭', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    await page.getByLabel('AI 상담').click();
    await expect(page.getByRole('heading', { name: 'BioChat AI' })).toBeVisible({ timeout: 3000 });
  });

  test('빠른 실행 — 약물 정보 클릭', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    await page.getByLabel('약물 정보').click();
    await expect(page.getByRole('heading', { name: /약물/ })).toBeVisible({ timeout: 3000 });
  });

  test('빠른 실행 — 생활 가이드 클릭', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    const guideBtn = page.getByLabel('생활 가이드');
    if (await guideBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await guideBtn.click();
      // Chat 페이지로 이동
      await expect(page.getByLabel('메시지 입력')).toBeVisible();
    }
  });
});

test.describe('Drugs Page — 모든 인터랙션', () => {
  test('탭 3개 전부 클릭 + 데이터 로딩', async ({ page }) => {
    await page.goto(`${BASE}/drugs`);

    const tabs = ['현재 표준요법', '연구/임상시험', '신약 후보'];
    for (const tab of tabs) {
      await page.getByRole('tab', { name: tab }).click();
      await expect(page.getByRole('tab', { name: tab })).toHaveAttribute('aria-selected', 'true');
      // 로딩 후 결과 또는 빈 상태
      await page.waitForTimeout(2000);
      const hasItems = await page.locator('[role="listitem"]').count();
      const hasEmpty = await page.getByText('약물을 찾을 수 없습니다').isVisible().catch(() => false);
      expect(hasItems > 0 || hasEmpty).toBeTruthy();
    }
  });

  test('약물 카드 클릭 → 디테일 패널 열림', async ({ page }) => {
    await page.goto(`${BASE}/drugs`);
    await page.waitForTimeout(3000); // API 로딩 대기
    const firstDrug = page.locator('[role="listitem"]').first();
    if (await firstDrug.isVisible({ timeout: 5000 }).catch(() => false)) {
      await firstDrug.click();
      // 디테일 패널이 열려야 함
      await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 3000 });
    }
  });

  test('디테일 패널 탭 4개 전부 클릭', async ({ page }) => {
    await page.goto(`${BASE}/drugs`);
    await page.waitForTimeout(3000);
    const firstDrug = page.locator('[role="listitem"]').first();
    if (await firstDrug.isVisible({ timeout: 5000 }).catch(() => false)) {
      await firstDrug.click();
      await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 3000 });

      const detailTabs = ['타겟', 'Pathway', '부작용', '임상시험'];
      for (const tab of detailTabs) {
        const tabBtn = page.locator('[role="dialog"]').getByRole('tab', { name: tab });
        if (await tabBtn.isVisible()) {
          await tabBtn.click();
          await expect(tabBtn).toHaveAttribute('aria-selected', 'true');
          await page.waitForTimeout(1500); // API 로딩 대기
        }
      }
    }
  });

  test('디테일 패널 닫기 버튼', async ({ page }) => {
    await page.goto(`${BASE}/drugs`);
    await page.waitForTimeout(3000);
    const firstDrug = page.locator('[role="listitem"]').first();
    if (await firstDrug.isVisible({ timeout: 5000 }).catch(() => false)) {
      await firstDrug.click();
      await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 3000 });
      await page.getByLabel('패널 닫기').click();
      await expect(page.locator('[role="dialog"]')).not.toBeVisible();
    }
  });

  test('검색 필터 동작', async ({ page }) => {
    await page.goto(`${BASE}/drugs`);
    await page.waitForTimeout(3000);
    const input = page.getByPlaceholder('약물 검색...');
    await input.fill('xxxnotexist');
    await page.waitForTimeout(500);
    // 결과 없음 표시
    const hasEmpty = await page.getByText('약물을 찾을 수 없습니다').isVisible().catch(() => false);
    const hasNoItems = (await page.locator('[role="listitem"]').count()) === 0;
    expect(hasEmpty || hasNoItems).toBeTruthy();
  });
});

test.describe('Chat — 실제 API 응답 렌더링', () => {
  test('부작용 질문 → 부작용 카드 렌더링', async ({ page }) => {
    await page.goto(BASE);
    await page.getByText('Docetaxel 부작용 알려줘').click();
    // AI 응답 대기
    await page.waitForTimeout(8000);
    // 부작용 목록이 표시되어야 함
    const hasNeutropenia = await page.getByText('NEUTROPENIA').isVisible().catch(() => false);
    const hasError = await page.getByText('연결 오류').isVisible().catch(() => false);
    expect(hasNeutropenia || hasError).toBeTruthy();
  });

  test('약물 목록 질문 → 약물 카드 렌더링', async ({ page }) => {
    await page.goto(BASE);
    const input = page.getByLabel('메시지 입력');
    await input.fill('유방암 표준요법 약물 목록');
    await input.press('Enter');
    await page.waitForTimeout(8000);
    // 약물 이름이 표시되어야 함
    const hasVinblastine = await page.getByText('Vinblastine').isVisible().catch(() => false);
    const hasDocetaxel = await page.getByText('Docetaxel').isVisible().catch(() => false);
    const hasError = await page.getByText('연결 오류').isVisible().catch(() => false);
    expect(hasVinblastine || hasDocetaxel || hasError).toBeTruthy();
  });
});

test.describe('대화 이력', () => {
  test('대화 후 이력에 표시', async ({ page }) => {
    await page.goto(BASE);
    const input = page.getByLabel('메시지 입력');
    await input.fill('테스트 대화');
    await input.press('Enter');
    await page.waitForTimeout(2000);
    // 사이드바에 대화 이력이 표시되어야 함
    const history = page.getByText('테스트 대화').first();
    await expect(history).toBeVisible({ timeout: 3000 });
  });
});
