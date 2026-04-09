# 🧬 20260409 Scaleup BISO - Drug Repurposing Knowledge Graph

## 📌 프로젝트 개요
유방암 약물 재창출 파이프라인 스케일업
- Neo4j Aura Free 기반 Knowledge Graph 구축
- FastAPI 백엔드 API 서버
- 다중 암종 확장 가능한 범용 구조

## 🚀 서버 실행
bash start_server.sh
- Swagger UI: http://localhost:8000/docs
- 외부 접속: https://beau-immusical-rina.ngrok-free.dev/docs

## 📡 API 엔드포인트 (12개)
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | /api/drugs | 약물 목록 |
| GET | /api/drug/{name} | 약물 상세 |
| GET | /api/drug/{name}/targets | 타겟 |
| GET | /api/drug/{name}/side_effects | 부작용 |
| GET | /api/drug/{name}/trials | 임상시험 |
| GET | /api/drug/{name}/pathways | Pathway |
| GET | /api/hospitals | 병원 목록 |
| GET | /api/disease/{code} | 질환 정보 |
| GET | /api/pubmed | 논문 검색 |
| GET | /api/ncis/{category} | 국립암센터 |
| GET | /api/stats | KG 통계 |
| POST | /api/chat | 채팅 질의 |

상세 명세: docs/API_SPEC.md

## 📊 Knowledge Graph 현황
| 노드 | 수량 | 엣지 | 수량 |
|------|------|------|------|
| Drug | 19,844 | TESTED_IN | 89,470 |
| Target | 8,880 | INTERACTS_WITH | 46,882 |
| CellLine | 969 | IN_PATHWAY | 729 |
| Trial | 155 | HAS_SIDE_EFFECT | 109 |
| Hospital | 97 | TARGETS | 41 |
| SideEffect | 46 | IN_TRIAL | 159 |
| Pathway | 686 | TREATS | 13 |
| Disease | 1 (BRCA) | | |

## 🗂️ 폴더 구조
- chat/api_server.py → FastAPI 서버
- llm/ → LLM 모듈 (뉴스/생활가이드/유명인)
- api/ → 외부 API 연동
- neo4j/ → 스키마 + 로더
- config/diseases/ → 암종별 YAML
- docs/ → API 명세서 + Joe 가이드

## 🔧 환경 설정
conda create -n drug4-kg python=3.10 -y
conda activate drug4-kg
pip install -r requirements.txt

## 🌿 암종 추가 방법 (팀원용)
config/diseases/LUAD.yaml 추가 후:
python neo4j/loaders/load_pipeline_results.py --disease LUAD

## 📅 진행 현황
| 항목 | 상태 |
|------|------|
| Neo4j KG 구축 | ✅ 완료 |
| FastAPI 서버 | ✅ 완료 |
| FAERS/ClinicalTrials/CRIS | ✅ 완료 |
| ChEMBL/PubChem/UniProt | ✅ 완료 |
| HIRA 병원정보 | ✅ 97개 |
| HIRA 약가/전문병원/비급여 | ⏳ 20260410 재시도 |
| 국립암센터 협력병기 | ⏳ 수동심의 대기 |
| Bedrock 연동 | 📋 추후 예정 |
| Neptune 마이그레이션 | 📋 200MB 초과 시 |

## 👥 프론트엔드 (Joe)
- 노션 가이드: https://www.notion.so/33dc603002ec81e990bbe2742e9ee1f3
- API 명세서: docs/API_SPEC.md
- 구현 가이드: docs/FOR_JOE_FRONTEND.md
