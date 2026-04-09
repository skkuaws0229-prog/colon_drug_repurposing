# 프론트엔드 개발자 Joe에게

## API 접속 URL

**ngrok 공개 URL (원격 접속용):**
- Base URL: `(ngrok URL - 서버 시작 시 공유)`
- Swagger UI: `{ngrok URL}/docs`
- 무료 플랜은 서버 재시작 시 URL 변경됨 → 변경 시 카카오톡/슬랙으로 공유

**로컬 접속:**
- Base URL: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- 상세 명세: `docs/API_SPEC.md`

## 빠른 시작

```bash
# 방법 1: 서버 + ngrok 동시 실행 (추천)
cd 20260409_scaleup_biso
./start_server.sh

# 방법 2: 수동 실행
cd 20260409_scaleup_biso
conda activate drug4-kg
uvicorn chat.api_server:app --reload --port 8000
# 다른 터미널에서: ngrok http 8000
```

ngrok 실행 후 터미널에 표시되는 `https://xxxx.ngrok-free.app` URL이 공개 접속 주소

## Neo4j 비밀번호
별도 전달 예정 (보안상 문서 미포함)
`.env` 파일에 아래 형식으로 저장:
```
NEO4J_URI=neo4j+s://108928fe.databases.neo4j.io
NEO4J_USERNAME=108928fe
NEO4J_DATABASE=108928fe
NEO4J_PASSWORD=(별도 전달)
```

## 주요 사용 시나리오

### 환자/보호자 화면
| 기능 | API | 예시 |
|------|-----|------|
| 약물 목록 | `GET /api/drugs?status=BRCA_CURRENT` | 현재 표준요법 6개 |
| 병원 찾기 | `GET /api/hospitals?region=서울` | 서울 지역 병원 |
| 부작용 확인 | `GET /api/drug/Docetaxel/side_effects` | NEUTROPENIA, NAUSEA 등 |
| 임상시험 | `GET /api/drug/Docetaxel/trials` | NCT ID, 모집 상태 |
| 생활가이드 | `GET /api/ncis/guide` | 국립암센터 생활백서 |
| 최신 뉴스 | `POST /api/chat` + `"유방암 최신 뉴스"` | 뉴스 검색 |
| 추천 음식 | `POST /api/chat` + `"추천 음식"` | 생활 가이드 |

### 연구자 화면
| 기능 | API | 예시 |
|------|-----|------|
| 파이프라인 약물 | `GET /api/drugs?pipeline=true` | 15개 약물 (랭킹순) |
| 타겟 분석 | `GET /api/drug/Docetaxel/targets` | NR1I2, TUBB1, BCL2 |
| Pathway | `GET /api/drug/Docetaxel/pathways` | Reactome pathway |
| 논문 검색 | `GET /api/pubmed?query=breast+cancer+docetaxel` | PubMed 실시간 |
| KG 통계 | `GET /api/stats` | 30,558 노드 / 137,465 엣지 |

### 채팅 어시스턴트
```bash
POST /api/chat
Content-Type: application/json

{
  "query": "Docetaxel 부작용 알려줘",
  "user_type": "patient"
}
```
- `user_type`: `patient` (환자/보호자) 또는 `researcher` (연구자)
- 자연어 질의 → 자동 의도 분류 → Neo4j/PubMed/NCIS 조회 → 결과 반환

**지원 질의 예시:**
- "Docetaxel 부작용 알려줘" → 부작용 목록
- "Paclitaxel 임상시험" → 임상시험 목록
- "유방암 통계" → 환자 수 통계
- "병원 목록" → 유방암 치료 병원
- "유방암 예방" → 국립암센터 예방 정보
- "유방암 최신 뉴스" → 뉴스 검색
- "유방암 환자 추천 음식" → 생활 가이드

## 응답 형식 (공통)
```json
{
  "status": "success",
  "data": { ... },
  "source": "neo4j | pubmed | ncis | news",
  "timestamp": "2026-04-09T09:05:33+00:00"
}
```

## brca_status 분류
| 값 | 의미 | 수 |
|----|------|-----|
| `BRCA_CURRENT` | 유방암 현재 표준요법 | 6개 |
| `BRCA_RESEARCH` | 유방암 연구/임상시험 중 | 5개 |
| `BRCA_CANDIDATE` | 유방암 신약 재창출 후보 | 4개 |

## CORS
현재 전체 허용 상태 (`allow_origins=["*"]`) — 개발 환경용
프로덕션 배포 시 도메인 제한 필요
