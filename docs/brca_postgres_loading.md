# BRCA PostgreSQL 적재 운영 문서

## 1. 목적
이 문서는 BRCA 약물 재창출 결과를 S3에서 PostgreSQL(`Drug`)로 적재하고 검증하는 표준 운영 절차를 팀 공용으로 정리한 문서입니다.

## 2. 현재 기준 환경
- 프로젝트 루트: `C:\work\drug-project`
- DB 접속 정보:
  - host=`localhost`
  - port=`5432`
  - db=`Drug`
  - user=`Drug`
  - password=`1234`
- psql 경로: `C:\Program Files\PostgreSQL\18\bin\psql.exe`
- BRCA 테이블은 이미 생성되어 있으며, 이 문서 절차는 테이블/DB 드롭을 수행하지 않습니다.

## 3. 적재 범위(고정)
- disease: `BRCA`
- run_id: `BRCA_RELEASE_V1`
- S3 base:
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260428_new_BRCA_data/`
- 주의:
  - BRCA 상위 폴더 전체 스캔 금지
  - CRC/LUAD/STAD/멀티캔서 폴더 적재 금지
  - prediction parquet 적재 금지(별도 요청 전까지)

## 4. 원커맨드 실행(권장)
아래 1개 명령으로 마이그레이션 + 로더 + 카운트 + 검증까지 모두 수행됩니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\db\run_brca_postgres_load.ps1
```

스크립트:
- [scripts/db/run_brca_postgres_load.ps1](C:/work/drug-project/scripts/db/run_brca_postgres_load.ps1)

스크립트 동작:
1. 프로젝트 루트 자동 계산(스크립트 위치 기준)
2. 인코딩 설정 (`chcp 65001`, `PGCLIENTENCODING=UTF8`)
3. DB 환경변수 설정
4. 필수 파일 체크
5. DB 연결 체크
6. `002_fix_model_metric_unique_key.sql` 실행
7. 로더 실행
8. 핵심 테이블 카운트 출력
9. `check_brca_table_counts.py` 실행(존재 시)
10. `check_brca_postgres_loaded.py` 실행(존재 시)

## 5. 수동 실행 절차(Manual)
```powershell
cd C:\work\drug-project

chcp 65001
$env:PGCLIENTENCODING="UTF8"
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
$env:POSTGRES_DB="Drug"
$env:POSTGRES_USER="Drug"
$env:POSTGRES_PASSWORD="1234"
$env:PGPASSWORD="1234"
```

1) DB 연결 확인
```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h localhost -p 5432 -U Drug -d Drug --set=client_encoding=UTF8 -c "SELECT current_database(), current_user;"
```

2) 모델 metric unique key 보정
```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h localhost -p 5432 -U Drug -d Drug --set=client_encoding=UTF8 -v ON_ERROR_STOP=1 -f .\scripts\db\002_fix_model_metric_unique_key.sql
```

3) 로더 실행
```powershell
python .\scripts\db\load_brca_results_to_postgres.py
```

4) 검증
```powershell
python .\scripts\db\check_brca_table_counts.py
python .\scripts\db\check_brca_postgres_loaded.py
```

## 6. 산출물
- Load report:
  - `outputs/db_validation/brca_postgres_load_report.json`
- Validation report:
  - `outputs/db_validation/brca_postgres_validation_report.json`

## 7. 데이터/키 설계 메모
- `id` 컬럼(UUID)는 비즈니스 의미가 아니라 기술적 고유 식별자입니다.
- 예: `011bfec7-e9dd-4449-b483-796f3ef30c56`
- `model_metric` 중복 이슈 해결:
  - `phase`, `family`, `source_model_dir`를 적재 필드로 포함
  - migration 파일에서 `uq_model_metric_v2` 인덱스 기준으로 고유성 보장

## 8. 최근 검증 통과 기준(row count)
- `brca_load_audit` = 16
- `run_manifest` = 1
- `source_artifact` = 1
- `drug_candidate_result` = 30
- `drug_candidate_tier` = 30
- `final_candidate_result` = 15
- `admet_result` = 30
- `admet_assay_match` = 58
- `admet_summary` = 6
- `external_validation_result` = 45
- `metabric_method_score` = 60
- `model_metric` = 215
- `model_metric_detailed` = 602
- `ensemble_metric` = 9
- `ensemble_source_manifest` = 5

## 9. 트러블슈팅
### 9.1 `psql`이 멈춘 것처럼 보임
- 증상:
  - STEP 5/6에서 진행이 안 됨
- 원인:
  - 비밀번호 프롬프트 대기
- 조치:
```powershell
$env:PGPASSWORD="1234"
```
재실행

### 9.2 `UniqueViolation: uq_model_metric`
- 증상:
  - `model_metric` 적재 중 duplicate key 오류
- 원인:
  - 동일 `model+metric` 조합이 phase/family/source context별로 반복
- 조치:
  - `002_fix_model_metric_unique_key.sql` 선적용
  - 로더는 최신 코드(phase/family/source_model_dir 포함) 사용

### 9.3 `python` 명령 인식 실패
- 증상:
  - `'python' is not recognized ...`
- 조치:
  - Python PATH 설정 또는 절대경로 실행
  - 예: `<repo-root>\AppData\Local\Programs\Python\Python311\python.exe`

### 9.4 잘못된 포트로 접속
- 증상:
  - connection refused
- 조치:
  - `POSTGRES_PORT=5432` 확인

### 9.5 한글 출력 깨짐
- 조치:
```powershell
chcp 65001
$env:PGCLIENTENCODING="UTF8"
```

### 9.6 S3 접근 오류
- 증상:
  - AccessDenied / credential error / missing key
- 조치:
  - AWS credential/profile 확인
  - 대상 prefix 권한(`HeadObject`, `GetObject`) 확인

### 9.7 재실행 시 중복 적재 우려
- 현재 로더는 `disease/run_id/source_s3_uri` 기준 `DELETE + INSERT` 전략 사용
- 같은 입력 파일 재실행 시 누적 중복 대신 교체 적재 동작
