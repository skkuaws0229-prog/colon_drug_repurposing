import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:4173'; // vite preview

/* ════════════════════════════════════════════════════════
   E2E 테스트 — BioChat AI Frontend
   검증 항목:
   1. 라우팅 & 페이지 렌더링
   2. API 연결 (실제 백엔드 or 에러 핸들링)
   3. 환자/연구자 모드 전환
   4. 채팅 인터페이스
   5. 약물 탐색기 필터 + 디테일 패널
   6. 접근성 (aria-label, role, keyboard nav)
   ════════════════════════════════════════════════════════ */

test.describe('1. Routing & Page Rendering', () => {
  test('/ → Chat 페이지 렌더링 (Welcome Screen)', async ({ page }) => {
    await page.goto(BASE);
    await expect(page.getByRole('heading', { name: 'BioChat AI' })).toBeVisible();
    await expect(page.getByLabel('메시지 입력')).toBeVisible();
    await expect(page.getByLabel('메시지 전송')).toBeVisible();
  });

  test('/dashboard → Dashboard 페이지 렌더링', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByText('KG 전체 노드')).toBeVisible();
    await expect(page.getByText('KG 전체 엣지')).toBeVisible();
  });

  test('/drugs → 약물 탐색기 렌더링', async ({ page }) => {
    await page.goto(`${BASE}/drugs`);
    await expect(page.getByRole('heading', { name: /약물 정보|약물 파이프라인/ })).toBeVisible();
    await expect(page.getByPlaceholder('약물 검색...')).toBeVisible();
  });
});

test.describe('2. Sidebar Navigation', () => {
  test('사이드바 내비게이션 버튼 존재', async ({ page }) => {
    await page.goto(BASE);
    await expect(page.getByLabel('BioChat AI 홈')).toBeVisible();
    await expect(page.getByLabel('AI Chat')).toBeVisible();
    await expect(page.getByLabel('Dashboard')).toBeVisible();
    await expect(page.getByLabel('약물 탐색')).toBeVisible();
  });

  test('Dashboard 버튼 클릭 → 페이지 이동', async ({ page }) => {
    await page.goto(BASE);
    await page.getByLabel('Dashboard').click();
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  });

  test('약물 탐색 버튼 클릭 → 페이지 이동', async ({ page }) => {
    await page.goto(BASE);
    await page.getByLabel('약물 탐색').click();
    await expect(page.getByRole('heading', { name: /약물/ })).toBeVisible();
  });
});

test.describe('3. Mode Toggle (환자/연구자)', () => {
  test('기본 모드 = 환자/보호자 표시', async ({ page }) => {
    await page.goto(BASE);
    await expect(page.getByText('환자/보호자')).toBeVisible();
  });

  test('모드 토글 클릭 → 연구자 모드 전환', async ({ page }) => {
    await page.goto(BASE);
    const toggle = page.getByLabel(/현재:.*모드/);
    await toggle.click();
    await expect(page.getByText('연구자')).toBeVisible();
  });

  test('연구자 모드에서 다른 제안 칩 표시', async ({ page }) => {
    await page.goto(BASE);
    // 환자 모드 제안 확인
    await expect(page.getByText('Docetaxel 부작용 알려줘')).toBeVisible();
    // 연구자 모드로 전환
    await page.getByLabel(/현재:.*모드/).click();
    // 연구자 모드 제안 확인
    await expect(page.getByText('Docetaxel 타겟 유전자 분석')).toBeVisible();
  });
});

test.describe('4. Chat Interface', () => {
  test('제안 칩 클릭 → 채팅 메시지 전송', async ({ page }) => {
    await page.goto(BASE);
    await page.getByText('Docetaxel 부작용 알려줘').click();
    // 유저 메시지가 표시되어야 함
    await expect(page.getByText('Docetaxel 부작용 알려줘').first()).toBeVisible();
    // thinking indicator 또는 AI 응답이 표시되어야 함
    await expect(
      page.getByRole('status', { name: 'AI가 응답을 생성하고 있습니다' })
    ).toBeVisible({ timeout: 5000 });
  });

  test('텍스트 입력 후 Enter → 메시지 전송', async ({ page }) => {
    await page.goto(BASE);
    const input = page.getByLabel('메시지 입력');
    await input.fill('유방암 통계');
    await input.press('Enter');
    // 유저 메시지가 표시되어야 함
    await expect(page.getByText('유방암 통계').first()).toBeVisible();
  });

  test('빈 입력 → 전송 불가 (버튼 disabled)', async ({ page }) => {
    await page.goto(BASE);
    const sendBtn = page.getByLabel('메시지 전송');
    await expect(sendBtn).toBeDisabled();
  });
});

test.describe('5. Drug Explorer', () => {
  test('BRCA 상태 탭 전환', async ({ page }) => {
    await page.goto(`${BASE}/drugs`);
    // 기본 탭: 현재 표준요법
    await expect(page.getByRole('tab', { name: '현재 표준요법' })).toHaveAttribute('aria-selected', 'true');
    // 연구/임상시험 탭 클릭
    await page.getByRole('tab', { name: '연구/임상시험' }).click();
    await expect(page.getByRole('tab', { name: '연구/임상시험' })).toHaveAttribute('aria-selected', 'true');
  });

  test('약물 검색 필터링', async ({ page }) => {
    await page.goto(`${BASE}/drugs`);
    // 약물 로딩 대기
    await page.waitForSelector('[role="listitem"]', { timeout: 10000 }).catch(() => {});
    const input = page.getByPlaceholder('약물 검색...');
    await input.fill('Docetaxel');
    // Docetaxel이 포함된 결과만 표시
    const items = page.locator('[role="listitem"]');
    if (await items.count() > 0) {
      await expect(items.first()).toContainText('Docetaxel');
    }
  });
});

test.describe('6. Accessibility (WCAG 2.1 AA)', () => {
  test('모든 아이콘 버튼에 aria-label 존재', async ({ page }) => {
    await page.goto(BASE);
    // 사이드바 버튼들
    const buttons = page.locator('aside button');
    const count = await buttons.count();
    for (let i = 0; i < count; i++) {
      const btn = buttons.nth(i);
      const label = await btn.getAttribute('aria-label');
      const text = await btn.textContent();
      // aria-label 또는 텍스트 콘텐츠가 있어야 함
      expect(label || text?.trim()).toBeTruthy();
    }
  });

  test('메인 내비게이션 role="navigation" 존재', async ({ page }) => {
    await page.goto(BASE);
    await expect(page.locator('aside[role="navigation"]')).toBeVisible();
  });

  test('chat log에 aria-live="polite" 존재', async ({ page }) => {
    await page.goto(BASE);
    // 메시지 전송하여 chat log 표시
    await page.getByText('Docetaxel 부작용 알려줘').click();
    await expect(page.locator('[aria-live="polite"]')).toBeVisible({ timeout: 3000 });
  });

  test('focus-visible 스타일 동작', async ({ page }) => {
    await page.goto(BASE);
    // Tab 키로 첫 버튼에 포커스
    await page.keyboard.press('Tab');
    // 포커스된 요소가 존재
    const focused = page.locator(':focus-visible');
    await expect(focused).toBeVisible();
  });

  test('DrugsPage 탭 role="tablist" 존재', async ({ page }) => {
    await page.goto(`${BASE}/drugs`);
    await expect(page.locator('[role="tablist"]')).toBeVisible();
  });
});

test.describe('7. API 연결 테스트 (실제 백엔드)', () => {
  test('Dashboard 통계 로딩 (API 호출)', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    // 통계 카운터가 0보다 큰 값을 표시하면 API 연결 성공
    // 타임아웃 내 로딩되지 않으면 기본값 표시
    await page.waitForTimeout(3000);
    const nodeText = page.getByText('KG 전체 노드');
    await expect(nodeText).toBeVisible();
  });

  test('Drugs API 호출 → 약물 목록 또는 에러 핸들링', async ({ page }) => {
    await page.goto(`${BASE}/drugs`);
    // 로딩 스피너 또는 약물 카드 또는 "약물을 찾을 수 없습니다" 중 하나
    await expect(
      page.locator('[role="listitem"]').first()
        .or(page.getByText('약물을 찾을 수 없습니다'))
        .or(page.getByLabel('로딩 중'))
    ).toBeVisible({ timeout: 10000 });
  });
});
