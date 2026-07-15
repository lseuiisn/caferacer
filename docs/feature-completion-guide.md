# WayPoint MVP 기능 완성 가이드

## 1. 이번 구현 범위

- 홈: 현재 GPS를 기준으로 가까운 카페 정렬, TMAP 마커, 필터, 목록 전환, 즐겨찾기, 상세, 정확한 TMAP 예상 거리·시간
- 코스: 오늘의 코스와 공개 번개코스 선택 필터, 지도 마커·경로, 상세, 랭킹, 주행 시작
- 공개 번개: 장소 검색 또는 지도 터치로 출발지·목적지 선택, 당일 공개, 참가, 두 가지 랭킹 방식
- 크루: 생성·가입·승인·초대, 크루원 목록, 채팅, 크루 전용 번개, 크루 오늘의 코스 랭킹
- 주행: 기록 생성, 외부 TMAP 자동 실행, Android 포그라운드 GPS, 종료 검증, 랭킹 반영 여부 표시
- 커뮤니티: 사진 5장, 글, 좋아요, 댓글, 본인 글·댓글 삭제, 신고, 사용자 차단
- 프로필: 사진·닉네임·소개 수정, 차량 등록·삭제, 주행 기록, 작성 글
- 관리자: 카페 후보 등록·승인, 오늘의 코스 설정, 코스 비활성화, 신고 처리

## 2. 주행 처리 순서

1. 사용자가 `주행 시작`을 누른다.
2. Flutter가 GPS 권한과 위치 서비스를 확인한다.
3. `POST /drive-records`로 기록을 생성한다.
4. 주행 화면을 먼저 연다.
5. Android TMAP SDK가 외부 TMAP 앱을 코스 시작점까지 자동 실행한다.
6. WayPoint는 포그라운드 위치 알림을 유지하며 약 10m 간격 GPS를 수집한다.
7. GPS 20개 단위로 `POST /drive-records/{id}/points`에 전송한다.
8. 종료 시 `POST /drive-records/{id}/complete`를 호출한다.
9. 서버는 정규 코스는 Path와 필수 Anchor, 번개코스는 출발지·목적지 반경을 검증한다.
10. 검증된 완주만 랭킹에 반영한다.

TMAP 실행이 실패하면 `POST /drive-records/{id}/cancel`로 빈 기록을 취소한다. TMAP은 시작점까지의 외부 길안내를 맡고, 정규 코스 완주는 우리 DB의 Path로 검증한다.

## 3. 랭킹 정책

- 오늘의 코스 기본 랭킹: 유효 완주 시간 오름차순
- 공개/크루 번개: 생성자가 `fastest` 또는 `closest_to_baseline` 선택
- 크루 오늘의 코스: 크루장 또는 매니저가 방식 선택
- 기준보다 빠른 기록: 파란색과 음수 퍼센트
- 기준보다 느린 기록: 빨간색과 양수 퍼센트
- 완주자가 없으면 `아직 검증 완료된 완주자가 없습니다.` 표시
- 모든 랭킹에 안전 운전 안내 표시

## 4. 주요 백엔드 파일

| 파일 | 역할 |
| --- | --- |
| `backend/app/models/social.py` | 공개 번개, 참가자, 크루 번개, 크루 오늘의 코스 랭킹, 커뮤니티·프로필 Entity |
| `backend/app/models/drive.py` | 정규·크루·공개 번개 주행 기록과 GPS 포인트 |
| `backend/alembic/versions/20260715_0006_lightning_and_crew_rankings.py` | 신규 테이블과 FK 마이그레이션 |
| `backend/app/api/routers/lightning_courses.py` | 공개 번개 조회·생성·참가·비활성화 |
| `backend/app/api/routers/drive_records.py` | 주행 시작·GPS 업로드·완료 검증·취소 |
| `backend/app/api/routers/rankings.py` | 정규·크루 번개·공개 번개 랭킹 |
| `backend/app/api/routers/crews.py` | 크루·멤버·초대·채팅·번개·크루 전용 랭킹 |
| `backend/app/api/routers/places.py` | TMAP 장소 검색 프록시 |
| `backend/app/api/routers/cafes.py` | 카페 필터·상세·즐겨찾기·TMAP 이동 예상 |
| `backend/app/api/routers/community.py` | 글·댓글·좋아요·신고·차단·내 글 |
| `backend/app/api/routers/admin_moderation.py` | 관리자 신고 조회·처리 |
| `backend/app/integrations/tmap.py` | TMAP 장소 검색·주소 변환·자동차 경로 예상 |

## 5. 주요 Flutter 파일

| 파일 | 역할 |
| --- | --- |
| `frontend/lib/features/cafes/presentation/cafe_list_screen.dart` | 홈 카페 지도·필터·즐겨찾기·상세 |
| `frontend/lib/features/courses/presentation/course_screen.dart` | 오늘의 코스/공개 번개 지도와 상세 |
| `frontend/lib/features/courses/presentation/lightning_course_form.dart` | 공개/크루 번개 생성, 장소 검색과 지도 좌표 선택 |
| `frontend/lib/features/drive_tracking/data/drive_tracking_service.dart` | 포그라운드 GPS 수집·배치 업로드·완료·취소 |
| `frontend/lib/features/drive_tracking/presentation/drive_session_screen.dart` | 실제 주행 상태·속도·시간·종료 결과 |
| `frontend/lib/features/navigation/data/tmap_navigation_gateway.dart` | Flutter에서 Android TMAP 플랫폼 채널 호출 |
| `frontend/android/app/src/main/kotlin/com/example/frontend/MainActivity.kt` | TMAP 앱 자동 길안내 실행 |
| `frontend/lib/features/rankings/presentation/ranking_sheet.dart` | 빈 상태, 안전 문구, ±% 색상 표시 |
| `frontend/lib/features/crews/presentation/crew_screen.dart` | 크루 가입·관리·채팅·번개·랭킹 |
| `frontend/lib/features/community/presentation/community_screen.dart` | 사진 게시물·댓글·좋아요·신고·차단 |
| `frontend/lib/features/profile/presentation/profile_screen.dart` | 프로필·차량·기록·작성 글·관리자 진입 |
| `frontend/lib/features/admin/presentation/admin_screen.dart` | 앱 내부 운영 도구 |

## 6. 추가 API

- `GET/POST /lightning-courses`
- `GET/DELETE /lightning-courses/{id}`
- `POST /lightning-courses/{id}/join`
- `GET /rankings/lightning-courses/{id}`
- `POST /drive-records/{id}/cancel`
- `GET /places/search?q=...`
- `POST /cafes/{id}/navigation`
- `GET /crews/{id}/members`
- `DELETE /crews/{id}/members/me`
- `GET/PUT /crews/{id}/daily-rankings`
- `GET /crews/{id}/daily-rankings/{course_id}`
- `GET /me/posts`
- `DELETE /comments/{id}`
- `GET/PATCH /admin/reports`

Swagger는 `http://127.0.0.1:8000/docs`에서 확인한다.

## 7. 로컬 실행과 확인

```powershell
cd D:\caferacerapp\backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

```powershell
cd D:\caferacerapp\frontend
flutter pub get
flutter run
```

Android 실기기에 TMAP 앱이 설치되어 있어야 자동 길안내를 시험할 수 있다. `frontend/android/local.properties`에는 `TMAP_MAP_API_KEY`가 있어야 하며 이 파일은 Git에 올리지 않는다.

## 8. 출시 전 ngrok 대체

ngrok은 개발 중 로컬 공유에만 사용한다. 출시 준비 단계에서는 다음을 분리한다.

1. FastAPI를 컨테이너화한다.
2. 관리형 HTTPS 서버 또는 클라우드 런타임에 배포한다.
3. MySQL은 외부 공개 포트를 닫은 관리형 DB 또는 사설망 DB로 이전한다.
4. 사진은 로컬 `media/` 대신 S3 호환 오브젝트 스토리지와 CDN으로 이전한다.
5. 비밀키는 `.env` 파일 대신 배포 환경의 Secret Manager에 보관한다.
6. 개발·스테이징·운영 API URL과 OAuth Redirect URI를 분리한다.
7. 로그 수집, 오류 추적, DB 백업, 개인정보 삭제 정책을 적용한 뒤 스토어 심사를 진행한다.

현재 로컬 미디어 방식은 MVP 개발에는 유지하지만, 여러 서버 인스턴스로 확장하기 전 반드시 오브젝트 스토리지로 변경한다.
