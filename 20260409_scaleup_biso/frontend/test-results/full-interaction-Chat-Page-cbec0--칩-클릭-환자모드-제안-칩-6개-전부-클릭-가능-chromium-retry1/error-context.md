# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: full-interaction.spec.ts >> Chat Page — 모든 제안 칩 클릭 >> 환자모드 제안 칩 6개 전부 클릭 가능
- Location: e2e/full-interaction.spec.ts:10:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('Docetaxel 부작용 알려줘')
Expected: visible
Timeout: 3000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 3000ms
  - waiting for getByText('Docetaxel 부작용 알려줘')

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - navigation "메인 내비게이션" [ref=e4]:
    - generic [ref=e5]:
      - button "BioChat AI 홈" [ref=e6]:
        - img [ref=e7]
      - generic [ref=e9]: BioChat AI
      - button "사이드바 접기" [ref=e10]:
        - img [ref=e11]
    - button "새 대화" [ref=e15]:
      - img [ref=e16]
      - generic [ref=e17]: 새 대화
    - generic [ref=e19]:
      - paragraph [ref=e20]: 대화 이력
      - generic [ref=e22] [cursor=pointer]:
        - img [ref=e23]
        - generic [ref=e25]: 유방암 표준요법 약물 목록 알려줘
        - button "유방암 표준요법 약물 목록 알려줘 삭제" [ref=e26]:
          - img [ref=e27]
    - navigation "페이지 이동" [ref=e30]:
      - button "AI Chat" [ref=e31]:
        - img [ref=e33]
        - generic [ref=e35]: AI Chat
      - button "Dashboard" [ref=e36]:
        - img [ref=e37]
        - generic [ref=e42]: Dashboard
      - button "약물 탐색" [ref=e43]:
        - img [ref=e44]
        - generic [ref=e47]: 약물 탐색
    - generic [ref=e48]:
      - generic [ref=e49]:
        - button "Dark 테마" [ref=e50]:
          - img [ref=e51]
          - text: Dark
        - button "Light 테마" [ref=e53]:
          - img [ref=e54]
          - text: Light
        - button "System 테마" [ref=e60]:
          - img [ref=e61]
          - text: System
      - 'button "현재: 환자/보호자 모드" [ref=e63]':
        - img [ref=e65]
        - generic [ref=e70]:
          - paragraph [ref=e71]: 환자/보호자
          - paragraph [ref=e72]: 모드 전환
  - main [ref=e73]:
    - generic [ref=e74]:
      - log "대화 내역" [ref=e75]:
        - generic [ref=e76]:
          - generic [ref=e77]:
            - generic [ref=e79]: U
            - paragraph [ref=e82]: 유방암 표준요법 약물 목록 알려줘
          - generic [ref=e83]:
            - img [ref=e85]
            - generic [ref=e88]:
              - generic [ref=e90]:
                - paragraph [ref=e92]: "유방암 현재 표준요법 약물 5개입니다:"
                - list "약물 목록" [ref=e94]:
                  - listitem [ref=e95]:
                    - generic [ref=e96]: "3"
                    - generic [ref=e97]: VinblastineMicrotubule destabiliser
                    - generic [ref=e98]: "13.3"
                  - listitem [ref=e99]:
                    - generic [ref=e100]: "5"
                    - generic [ref=e101]: DocetaxelMicrotubule stabiliser
                    - generic [ref=e102]: "12.8"
                  - listitem [ref=e103]:
                    - generic [ref=e104]: "7"
                    - generic [ref=e105]: VinorelbineMicrotubule destabiliser
                    - generic [ref=e106]: "12.5"
                  - listitem [ref=e107]:
                    - generic [ref=e108]: "10"
                    - generic [ref=e109]: PaclitaxelMicrotubule stabiliser
                    - generic [ref=e110]: "11.8"
                  - listitem [ref=e111]:
                    - generic [ref=e112]: "15"
                    - generic [ref=e113]: EpirubicinAnthracycline
                    - generic [ref=e114]: "3.3"
              - generic [ref=e115]: via neo4j
      - generic [ref=e116]:
        - generic [ref=e118]:
          - textbox "메시지 입력" [ref=e119]:
            - /placeholder: 궁금한 것을 물어보세요...
          - button "메시지 전송" [disabled] [ref=e120]:
            - img [ref=e121]
        - paragraph [ref=e124]: Neo4j Knowledge Graph · PubMed · NCIS
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | const BASE = 'http://localhost:4173';
  4   | 
  5   | /* ════════════════════════════════════════════════
  6   |    전수 인터랙션 테스트 — 모든 클릭 가능 요소 점검
  7   |    ════════════════════════════════════════════════ */
  8   | 
  9   | test.describe('Chat Page — 모든 제안 칩 클릭', () => {
  10  |   test('환자모드 제안 칩 6개 전부 클릭 가능', async ({ page }) => {
  11  |     await page.goto(BASE);
  12  |     const chips = [
  13  |       '유방암 표준요법 약물 목록 알려줘',
  14  |       'Docetaxel 부작용 알려줘',
  15  |       '서울 지역 유방암 치료 병원',
  16  |       'Paclitaxel 임상시험 정보',
  17  |       '유방암 예방 생활 가이드',
  18  |       '유방암 환자 추천 음식',
  19  |     ];
  20  |     for (const chip of chips) {
  21  |       // 매번 새 대화로 리셋
  22  |       await page.goto(BASE);
  23  |       const btn = page.getByText(chip, { exact: false });
> 24  |       await expect(btn).toBeVisible({ timeout: 3000 });
      |                         ^ Error: expect(locator).toBeVisible() failed
  25  |       await btn.click();
  26  |       // 유저 메시지가 대화에 표시되어야 함
  27  |       await expect(page.locator('[role="log"]')).toBeVisible({ timeout: 5000 });
  28  |       // thinking indicator 또는 AI 응답
  29  |       const hasThinking = await page.getByRole('status', { name: 'AI가 응답을 생성하고 있습니다' }).isVisible().catch(() => false);
  30  |       const hasLog = await page.locator('[role="log"]').isVisible();
  31  |       expect(hasThinking || hasLog).toBeTruthy();
  32  |     }
  33  |   });
  34  | 
  35  |   test('연구자모드 제안 칩 6개 전부 클릭 가능', async ({ page }) => {
  36  |     await page.goto(BASE);
  37  |     // 연구자 모드 전환
  38  |     await page.getByLabel(/현재:.*모드/).click();
  39  |     await expect(page.getByText('연구자')).toBeVisible();
  40  | 
  41  |     const chips = [
  42  |       'Docetaxel 타겟 유전자 분석',
  43  |       '파이프라인 약물 랭킹 보여줘',
  44  |       'Docetaxel pathway 조회',
  45  |       'breast cancer docetaxel PubMed',
  46  |       'Knowledge Graph 통계',
  47  |       '신약 재창출 후보 목록',
  48  |     ];
  49  |     for (const chip of chips) {
  50  |       await page.goto(BASE);
  51  |       // 연구자 모드 다시 전환 (페이지 이동 시 state 유지 확인)
  52  |       const modeBtn = page.getByLabel(/현재:.*모드/);
  53  |       const modeText = await page.getByText('연구자').isVisible().catch(() => false);
  54  |       if (!modeText) await modeBtn.click();
  55  | 
  56  |       const btn = page.getByText(chip, { exact: false });
  57  |       if (await btn.isVisible().catch(() => false)) {
  58  |         await btn.click();
  59  |         await expect(page.locator('[role="log"]')).toBeVisible({ timeout: 5000 });
  60  |       }
  61  |     }
  62  |   });
  63  | });
  64  | 
  65  | test.describe('Sidebar — 모든 버튼 동작', () => {
  66  |   test('로고 클릭 → 홈으로 이동', async ({ page }) => {
  67  |     await page.goto(`${BASE}/dashboard`);
  68  |     await page.getByLabel('BioChat AI 홈').click();
  69  |     await expect(page.getByRole('heading', { name: 'BioChat AI' })).toBeVisible({ timeout: 3000 });
  70  |   });
  71  | 
  72  |   test('사이드바 접기/펼치기', async ({ page }) => {
  73  |     await page.goto(BASE);
  74  |     // 접기
  75  |     const collapseBtn = page.getByLabel('사이드바 접기');
  76  |     if (await collapseBtn.isVisible()) {
  77  |       await collapseBtn.click();
  78  |       await expect(page.getByLabel('사이드바 펼치기')).toBeVisible();
  79  |       // 펼치기
  80  |       await page.getByLabel('사이드바 펼치기').click();
  81  |       await expect(page.getByLabel('사이드바 접기')).toBeVisible();
  82  |     }
  83  |   });
  84  | 
  85  |   test('새 대화 버튼', async ({ page }) => {
  86  |     await page.goto(BASE);
  87  |     // 먼저 메시지 전송
  88  |     const input = page.getByLabel('메시지 입력');
  89  |     await input.fill('테스트');
  90  |     await input.press('Enter');
  91  |     await page.waitForTimeout(1000);
  92  |     // 새 대화 클릭
  93  |     await page.getByLabel('새 대화').click();
  94  |     // Welcome screen이 다시 보여야 함
  95  |     await expect(page.getByRole('heading', { name: 'BioChat AI' })).toBeVisible({ timeout: 3000 });
  96  |   });
  97  | 
  98  |   test('테마 전환 (Dark → Light → Dark)', async ({ page }) => {
  99  |     await page.goto(BASE);
  100 |     // Light 클릭
  101 |     const lightBtn = page.getByLabel('Light 테마');
  102 |     if (await lightBtn.isVisible()) {
  103 |       await lightBtn.click();
  104 |       const theme = await page.locator('html').getAttribute('data-theme');
  105 |       expect(theme).toBe('light');
  106 |       // Dark로 돌아가기
  107 |       await page.getByLabel('Dark 테마').click();
  108 |       const theme2 = await page.locator('html').getAttribute('data-theme');
  109 |       expect(theme2).toBe('dark');
  110 |     }
  111 |   });
  112 | 
  113 |   test('모드 전환 반복', async ({ page }) => {
  114 |     await page.goto(BASE);
  115 |     const toggle = page.getByLabel(/현재:.*모드/);
  116 |     // 환자 → 연구자
  117 |     await toggle.click();
  118 |     await expect(page.getByText('연구자')).toBeVisible();
  119 |     // 연구자 → 환자
  120 |     await toggle.click();
  121 |     await expect(page.getByText('환자/보호자')).toBeVisible();
  122 |   });
  123 | });
  124 | 
```