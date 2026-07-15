# 코스 데이터 추가 가이드

## 입력 원칙

- 원본 경로는 GPX 트랙으로 관리한다.
- 출발지와 목적지는 각각 정확히 1개가 필요하다.
- 경유지는 출발지와 목적지를 제외하고 최대 10개다.
- 경로는 최소 2개, 최대 2,000개 좌표로 정규화한다.
- 같은 이름의 코스에 `--apply`를 다시 실행하면 코스, 경로, 경유지, 카페, 태그를 갱신한다.

## 1. GPX 준비

주행 후 내보낸 GPX를 `backend/data/raw_paths`에 저장한다. 개인정보 보호를 위해 집이나 회사처럼 민감한 출발 위치가 들어간 GPX는 바로 등록하지 말고 좌표를 제거한다.

## 2. JSON만 생성하여 검토

PowerShell에서 다음 명령을 실행한다.

```powershell
cd D:\caferacerapp\backend
..\.venv\Scripts\python.exe -m scripts.import_course `
  --gpx data\raw_paths\paldang.gpx `
  --name "팔당 강변 코스" `
  --region "경기도 남양주시" `
  --duration 120 `
  --difficulty normal `
  --season all `
  --time day `
  --moods riverside,scenic `
  --cafe-ids 1,2 `
  --waypoint-indexes 120,350
```

`--waypoint-indexes`는 변환된 경로 좌표 중 TMAP에 전달할 중간 지점의 순번이다. 10개를 초과하거나 출발/도착 좌표를 지정하면 검증에서 거절된다.

생성된 `data/generated_courses/*.json`에서 경로와 메타데이터를 검토한다.

## 3. MySQL 반영

검토한 동일 명령 끝에 `--apply`를 추가한다. `.env`의 `DATABASE_URL`이 운영 DB가 아닌 현재 개발 DB인지 먼저 확인한다.

```powershell
..\.venv\Scripts\python.exe -m scripts.import_course ... --apply
```

관리자 API로도 같은 구조를 등록할 수 있다.

- `POST /api/v1/admin/courses`: 신규 등록
- `PUT /api/v1/admin/courses/{course_id}`: 전체 갱신
- `DELETE /api/v1/admin/courses/{course_id}`: 비활성화

## 4. 등록 후 확인

```powershell
..\.venv\Scripts\python.exe -m pytest -q
```

Swagger의 `GET /api/v1/courses/{course_id}`에서 다음을 확인한다.

- path 좌표가 출발지부터 목적지까지 이어지는지
- navigation anchors가 순서대로 반환되는지
- 연결 카페와 태그가 맞는지
- 예상 거리와 시간이 실제 주행에 비해 과도하게 다르지 않은지

## 운영 권장 절차

코스 200개를 바로 공개하지 않고 `수집 → 내부 검수 → 시험 주행 → 활성화 → 일일 추천 지정` 단계를 거친다. 향후에는 관리자 웹에서 GPX 업로드, 지도 미리보기, 경유지 클릭 지정, 공개 승인까지 제공하도록 확장하는 것이 안전하다.
