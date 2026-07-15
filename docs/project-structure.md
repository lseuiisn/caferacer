# WayPoint 프로젝트 구조와 파일 역할

## 최상위

```text
D:\caferacerapp
├── backend/       FastAPI·SQLAlchemy·MySQL 서버
├── frontend/      Flutter·Riverpod 모바일 앱
├── docs/          아키텍처·ERD·API·데이터 운영 문서
├── .venv/         프로젝트 공용 Python 가상환경
└── .vscode/       로컬 개발 실행 설정
```

## Backend

```text
backend/
├── app/
│   ├── main.py                         FastAPI 앱 생성, OpenAPI 설정
│   ├── api/
│   │   ├── deps.py                     DB 세션·현재 사용자·관리자 의존성
│   │   ├── router.py                   모든 기능 Router 조립
│   │   └── routers/
│   │       ├── auth.py                 소셜 로그인·토큰·내 정보
│   │       ├── cafes.py                카페 목록·상세
│   │       ├── courses.py              코스 목록·상세·TMAP 실행 정보
│   │       ├── recommendations.py      조건 기반 코스 추천
│   │       ├── drive_records.py        GPS 업로드·완주 검증·기록 조회
│   │       └── admin.py                카페 후보 등록·운영자 승인
│   ├── core/
│   │   ├── config.py                   환경 변수 로딩
│   │   ├── database.py                 SQLAlchemy Engine·Session
│   │   └── security.py                 JWT·Refresh Token 보안 처리
│   ├── integrations/
│   │   └── tmap.py                     TMAP REST API 어댑터
│   ├── models/
│   │   ├── base.py                     Base·공통 생성/수정 시각
│   │   ├── enums.py                    상태·권한·Anchor 종류 Enum
│   │   ├── user.py                     사용자·소셜 계정·동의·세션 Entity
│   │   ├── catalog.py                  카페·코스·Path·NavigationAnchor Entity
│   │   └── drive.py                    주행 기록·GPS·Anchor 통과 Entity
│   ├── repositories/
│   │   ├── catalog.py                  카페·코스 DB 조회
│   │   ├── drive_records.py            사용자 주행 기록 DB 조회
│   │   └── user.py                     사용자 DB 접근
│   ├── schemas/
│   │   ├── auth.py                     인증 Request/Response
│   │   ├── catalog.py                  카페·코스 Response
│   │   ├── recommendations.py          추천·TMAP 실행 정보 Schema
│   │   ├── drive_records.py            GPS 배치·완주·기록 Schema
│   │   └── admin.py                    운영자 검수 Schema
│   └── services/
│       ├── auth.py                     인증 도메인 로직
│       ├── oauth.py                    카카오·구글 토큰 검증
│       └── drive_tracking.py           거리·Path 통과율·Anchor 검증
├── alembic/versions/
│   ├── 20260710_0001_initial_schema.py 초기 사용자·카페·코스
│   ├── 20260712_0002_course_centric_routes.py CoursePath 전환
│   ├── 20260712_0003_cafe_import_review.py 관리자 카페 검수
│   └── 20260715_0004_drive_tracking.py TMAP Anchor·GPS 주행 기록
├── scripts/                             시드·주소 검증·관리자 지정
├── data/                                검수된 초기 데이터
├── .env                                 로컬 비밀값, Git 제외
└── pyproject.toml                       Python 의존성·검사 설정
```

Router는 HTTP 처리만 담당하고, 계산은 Service, SQL은 Repository, 테이블은 Model,
입출력 검증은 Schema로 분리한다.

## Frontend

```text
frontend/lib/
├── main.dart                            SDK 초기화·ProviderScope
├── app/
│   ├── app.dart                         MaterialApp과 전역 Theme
│   ├── app_shell.dart                   5개 하단 탭과 탭 상태 유지
│   └── theme/app_theme.dart             공통 색상·Material 3 테마
├── core/
│   └── config/app_environment.dart      API·카카오 키 빌드 환경 설정
└── features/
    ├── auth/                            카카오·구글 로그인과 서비스 토큰 교환
    └── cafes/                           카페 모델·API·Riverpod 목록 화면
```

추가할 Flutter 기능 폴더는 다음과 같다.

```text
features/
├── home_map/          TMAP 지도·현재 위치·카페 마커·필터
├── favorites/         카페 즐겨찾기
├── courses/           일일 추천·탐색·상세·TMAP 실행
├── drive_tracking/    권한·백그라운드 GPS·배치 업로드·완료
├── rankings/          코스/크루 랭킹과 +/- 표시
├── community/         게시물·댓글·좋아요·신고
├── crews/             공개/초대 크루·멤버·대화·코스
└── profile/           사용자·차량·기록·작성 글
```

현재 `AppShell`의 코스·커뮤니티·크루·프로필은 구조를 먼저 고정한 임시 화면이다.
Figma 작업이 완료되는 순서대로 각 feature의 Presentation 계층으로 교체한다.

## 환경별 실행

민감하거나 환경마다 다른 값은 Dart 코드에 직접 저장하지 않는다.

```powershell
flutter run `
  --dart-define=API_BASE_URL=https://dev-api.example.com/api/v1 `
  --dart-define=KAKAO_NATIVE_APP_KEY=발급값
```

운영에서는 ngrok이 아니라 HTTPS 도메인과 배포 환경별 설정을 사용한다.

Python 스크립트는 공용 가상환경의 다른 editable 설치본을 잘못 읽지 않도록
`backend` 폴더에서 `python -m scripts.seed_catalog ...` 형식으로 실행한다.
