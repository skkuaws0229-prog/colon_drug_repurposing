# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: full-interaction.spec.ts >> Chat — 실제 API 응답 렌더링 >> 부작용 질문 → 부작용 카드 렌더링
- Location: e2e/full-interaction.spec.ts:231:3

# Error details

```
Error: expect(received).toBeTruthy()

Received: false
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
        - generic [ref=e25]: Docetaxel 부작용 알려줘
        - button "Docetaxel 부작용 알려줘 삭제" [ref=e26]:
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
            - paragraph [ref=e82]: Docetaxel 부작용 알려줘
          - generic [ref=e83]:
            - img [ref=e85]
            - generic [ref=e88]:
              - generic [ref=e90]:
                - paragraph [ref=e92]: "Docetaxel의 주요 부작용: NEUTROPENIA, NAUSEA, ALOPECIA, MADAROSIS, HAIR TEXTURE ABNORMAL"
                - list "부작용 목록" [ref=e94]:
                  - listitem [ref=e95]:
                    - generic [ref=e97]: NEUTROPENIA
                    - generic [ref=e98]: (NEUTROPENIA)
                  - listitem [ref=e99]:
                    - generic [ref=e101]: NAUSEA
                    - generic [ref=e102]: (NAUSEA)
                  - listitem [ref=e103]:
                    - generic [ref=e105]: ALOPECIA
                    - generic [ref=e106]: (ALOPECIA)
                  - listitem [ref=e107]:
                    - generic [ref=e109]: MADAROSIS
                    - generic [ref=e110]: (MADAROSIS)
                  - listitem [ref=e111]:
                    - generic [ref=e113]: HAIR TEXTURE ABNORMAL
                    - generic [ref=e114]: (HAIR TEXTURE ABNORMAL)
                  - listitem [ref=e115]:
                    - generic [ref=e117]: HAIR COLOUR CHANGES
                    - generic [ref=e118]: (HAIR COLOUR CHANGES)
                  - listitem [ref=e119]:
                    - generic [ref=e121]: HAIR DISORDER
                    - generic [ref=e122]: (HAIR DISORDER)
                  - listitem [ref=e123]:
                    - generic [ref=e125]: DIARRHOEA
                    - generic [ref=e126]: (DIARRHOEA)
                  - listitem [ref=e127]:
                    - generic [ref=e129]: EMOTIONAL DISTRESS
                    - generic [ref=e130]: (EMOTIONAL DISTRESS)
                  - listitem [ref=e131]:
                    - generic [ref=e133]: ANXIETY
                    - generic [ref=e134]: (ANXIETY)
              - generic [ref=e135]: via neo4j
      - generic [ref=e136]:
        - generic [ref=e138]:
          - textbox "메시지 입력" [ref=e139]:
            - /placeholder: 궁금한 것을 물어보세요...
          - button "메시지 전송" [disabled] [ref=e140]:
            - img [ref=e141]
        - paragraph [ref=e144]: Neo4j Knowledge Graph · PubMed · NCIS
```

# Test source

```ts
  139 |   });
  140 | 
  141 |   test('빠른 실행 — 약물 정보 클릭', async ({ page }) => {
  142 |     await page.goto(`${BASE}/dashboard`);
  143 |     await page.getByLabel('약물 정보').click();
  144 |     await expect(page.getByRole('heading', { name: /약물/ })).toBeVisible({ timeout: 3000 });
  145 |   });
  146 | 
  147 |   test('빠른 실행 — 생활 가이드 클릭', async ({ page }) => {
  148 |     await page.goto(`${BASE}/dashboard`);
  149 |     const guideBtn = page.getByLabel('생활 가이드');
  150 |     if (await guideBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
  151 |       await guideBtn.click();
  152 |       // Chat 페이지로 이동
  153 |       await expect(page.getByLabel('메시지 입력')).toBeVisible();
  154 |     }
  155 |   });
  156 | });
  157 | 
  158 | test.describe('Drugs Page — 모든 인터랙션', () => {
  159 |   test('탭 3개 전부 클릭 + 데이터 로딩', async ({ page }) => {
  160 |     await page.goto(`${BASE}/drugs`);
  161 | 
  162 |     const tabs = ['현재 표준요법', '연구/임상시험', '신약 후보'];
  163 |     for (const tab of tabs) {
  164 |       await page.getByRole('tab', { name: tab }).click();
  165 |       await expect(page.getByRole('tab', { name: tab })).toHaveAttribute('aria-selected', 'true');
  166 |       // 로딩 후 결과 또는 빈 상태
  167 |       await page.waitForTimeout(2000);
  168 |       const hasItems = await page.locator('[role="listitem"]').count();
  169 |       const hasEmpty = await page.getByText('약물을 찾을 수 없습니다').isVisible().catch(() => false);
  170 |       expect(hasItems > 0 || hasEmpty).toBeTruthy();
  171 |     }
  172 |   });
  173 | 
  174 |   test('약물 카드 클릭 → 디테일 패널 열림', async ({ page }) => {
  175 |     await page.goto(`${BASE}/drugs`);
  176 |     await page.waitForTimeout(3000); // API 로딩 대기
  177 |     const firstDrug = page.locator('[role="listitem"]').first();
  178 |     if (await firstDrug.isVisible({ timeout: 5000 }).catch(() => false)) {
  179 |       await firstDrug.click();
  180 |       // 디테일 패널이 열려야 함
  181 |       await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 3000 });
  182 |     }
  183 |   });
  184 | 
  185 |   test('디테일 패널 탭 4개 전부 클릭', async ({ page }) => {
  186 |     await page.goto(`${BASE}/drugs`);
  187 |     await page.waitForTimeout(3000);
  188 |     const firstDrug = page.locator('[role="listitem"]').first();
  189 |     if (await firstDrug.isVisible({ timeout: 5000 }).catch(() => false)) {
  190 |       await firstDrug.click();
  191 |       await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 3000 });
  192 | 
  193 |       const detailTabs = ['타겟', 'Pathway', '부작용', '임상시험'];
  194 |       for (const tab of detailTabs) {
  195 |         const tabBtn = page.locator('[role="dialog"]').getByRole('tab', { name: tab });
  196 |         if (await tabBtn.isVisible()) {
  197 |           await tabBtn.click();
  198 |           await expect(tabBtn).toHaveAttribute('aria-selected', 'true');
  199 |           await page.waitForTimeout(1500); // API 로딩 대기
  200 |         }
  201 |       }
  202 |     }
  203 |   });
  204 | 
  205 |   test('디테일 패널 닫기 버튼', async ({ page }) => {
  206 |     await page.goto(`${BASE}/drugs`);
  207 |     await page.waitForTimeout(3000);
  208 |     const firstDrug = page.locator('[role="listitem"]').first();
  209 |     if (await firstDrug.isVisible({ timeout: 5000 }).catch(() => false)) {
  210 |       await firstDrug.click();
  211 |       await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 3000 });
  212 |       await page.getByLabel('패널 닫기').click();
  213 |       await expect(page.locator('[role="dialog"]')).not.toBeVisible();
  214 |     }
  215 |   });
  216 | 
  217 |   test('검색 필터 동작', async ({ page }) => {
  218 |     await page.goto(`${BASE}/drugs`);
  219 |     await page.waitForTimeout(3000);
  220 |     const input = page.getByPlaceholder('약물 검색...');
  221 |     await input.fill('xxxnotexist');
  222 |     await page.waitForTimeout(500);
  223 |     // 결과 없음 표시
  224 |     const hasEmpty = await page.getByText('약물을 찾을 수 없습니다').isVisible().catch(() => false);
  225 |     const hasNoItems = (await page.locator('[role="listitem"]').count()) === 0;
  226 |     expect(hasEmpty || hasNoItems).toBeTruthy();
  227 |   });
  228 | });
  229 | 
  230 | test.describe('Chat — 실제 API 응답 렌더링', () => {
  231 |   test('부작용 질문 → 부작용 카드 렌더링', async ({ page }) => {
  232 |     await page.goto(BASE);
  233 |     await page.getByText('Docetaxel 부작용 알려줘').click();
  234 |     // AI 응답 대기
  235 |     await page.waitForTimeout(8000);
  236 |     // 부작용 목록이 표시되어야 함
  237 |     const hasNeutropenia = await page.getByText('NEUTROPENIA').isVisible().catch(() => false);
  238 |     const hasError = await page.getByText('연결 오류').isVisible().catch(() => false);
> 239 |     expect(hasNeutropenia || hasError).toBeTruthy();
      |                                        ^ Error: expect(received).toBeTruthy()
  240 |   });
  241 | 
  242 |   test('약물 목록 질문 → 약물 카드 렌더링', async ({ page }) => {
  243 |     await page.goto(BASE);
  244 |     const input = page.getByLabel('메시지 입력');
  245 |     await input.fill('유방암 표준요법 약물 목록');
  246 |     await input.press('Enter');
  247 |     await page.waitForTimeout(8000);
  248 |     // 약물 이름이 표시되어야 함
  249 |     const hasVinblastine = await page.getByText('Vinblastine').isVisible().catch(() => false);
  250 |     const hasDocetaxel = await page.getByText('Docetaxel').isVisible().catch(() => false);
  251 |     const hasError = await page.getByText('연결 오류').isVisible().catch(() => false);
  252 |     expect(hasVinblastine || hasDocetaxel || hasError).toBeTruthy();
  253 |   });
  254 | });
  255 | 
  256 | test.describe('대화 이력', () => {
  257 |   test('대화 후 이력에 표시', async ({ page }) => {
  258 |     await page.goto(BASE);
  259 |     const input = page.getByLabel('메시지 입력');
  260 |     await input.fill('테스트 대화');
  261 |     await input.press('Enter');
  262 |     await page.waitForTimeout(2000);
  263 |     // 사이드바에 대화 이력이 표시되어야 함
  264 |     const history = page.getByText('테스트 대화').first();
  265 |     await expect(history).toBeVisible({ timeout: 3000 });
  266 |   });
  267 | });
  268 | 
```