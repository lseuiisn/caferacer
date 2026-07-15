# WayPoint MVP REST API 명세

기본 URL은 `/api/v1`이다. 시간은 ISO 8601 UTC로 교환한다. 보호된 API에는 `Authorization: Bearer <access_token>` 헤더가 필요하다.

## 서비스 원칙

- 홈에서는 `Cafe`, 코스 탭에서는 `Course`가 각각 메인 리소스다.
- `Cafe`는 지도에서 독립 탐색할 수 있고 코스의 휴식 포인트로도 재사용된다.
- 코스의 실제 주행 Path는 서비스 DB의 `CoursePath`가 관리한다.
- 외부 TMAP 앱은 시작점·핵심 경유지·도착점 길안내를 담당한다.
- WayPoint는 백그라운드 GPS로 전체 Path 및 필수 경유지 통과를 검증한다.

## 인증

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `POST` | `/auth/social/login` | 카카오 Access Token 또는 Google ID Token 검증 후 서비스 JWT 발급 |
| `POST` | `/auth/refresh` | Refresh Token으로 토큰 재발급 |
| `POST` | `/auth/logout` | 현재 Refresh Token 폐기 |
| `GET` | `/auth/me` | 현재 사용자와 연결된 소셜 제공자 조회 |

## 코스

### `GET /courses`

드라이브 코스 목록을 반환한다.

| Query | 형식 | 설명 |
| --- | --- | --- |
| `region` | string | 광역 지역. `경기도`는 `경기도 가평`처럼 해당 값으로 시작하는 코스를 포함한다. |
| `duration_minutes` | integer | 이 시간 이하의 예상 코스만 반환한다. |
| `mood` | string, 반복 가능 | 모든 분위기 태그를 만족하는 코스만 반환한다. |
| `season` | string | `spring`, `summer`, `autumn`, `winter` 등. `all` 코스도 포함한다. |
| `difficulty` | string | `easy`, `normal`, `hard` 등 난이도. |
| `page` | integer | 기본값 `1` |
| `size` | integer | 기본값 `20`, 최대 `50` |

응답 항목에는 `id`, `name`, `description`, `region`, `estimated_duration_minutes`, `estimated_distance_meters`, `difficulty`, `recommended_season`, `recommended_time`, `thumbnail_url`, `cafe_count`, `moods`가 포함된다.

### `GET /courses/{course_id}`

코스 상세와 DB 관리 Path, 휴식 카페를 반환한다.

```json
{
  "id": 1,
  "name": "가평 드라이브 코스",
  "description": "강변 풍경을 따라 달리는 코스",
  "estimated_duration_minutes": 120,
  "estimated_distance_meters": 45000,
  "path": {
    "type": "polyline",
    "coordinates": [[37.71, 127.45], [37.72, 127.46]]
  },
  "path_points": [
    {
      "sequence": 1,
      "latitude": 37.71,
      "longitude": 127.45,
      "road_name": "북한강로",
      "road_type": "national"
    }
  ],
  "cafes": [
    {"id": 1, "name": "휴식 카페", "stop_order": 1, "tags": ["riverside"]}
  ]
}
```

`path.coordinates`의 순서는 `[latitude, longitude]`이며 Flutter에서 폴리라인을 그리는 기준이다.

### `POST /courses/{course_id}/navigation`

현재 위치에서 코스 시작점까지의 예상 정보와 외부 TMAP에 전달할 핵심 지점을 반환한다.
이 API 호출 전에 위치 권한을 확인하고, TMAP 실행 직전에 `POST /drive-records`로 기록을 만든다.

요청:

```json
{
  "origin": {"latitude": 37.5665, "longitude": 126.9780}
}
```

응답:

```json
{
  "distance_meters": 18200,
  "duration_seconds": 1560,
  "start_point": {"latitude": 37.622, "longitude": 127.312},
  "provider": "tmap",
  "requires_background_location": true,
  "anchors": [
    {
      "sequence": 0,
      "name": "코스 시작점",
      "anchor_type": "start",
      "latitude": 37.622,
      "longitude": 127.312,
      "pass_radius_meters": 100
    },
    {
      "sequence": 1,
      "name": "북한강 경유지",
      "anchor_type": "waypoint",
      "latitude": 37.700,
      "longitude": 127.400,
      "pass_radius_meters": 100
    }
  ]
}
```

호환성 변경: 기존 응답 필드는 유지되며 `provider`, `requires_background_location`,
`anchors`가 필수 필드로 추가된다.

## 추천

### `POST /recommendations`

사용자 조건에 맞는 드라이브 코스를 먼저 추천하고, 해당 코스에 포함된 조건 일치 카페를 반환한다.

요청:

```json
{
  "origin": {"latitude": 37.5665, "longitude": 126.9780},
  "round_trip_minutes": 180,
  "moods": ["riverside"],
  "season": "autumn",
  "difficulty": "normal",
  "filters": {
    "parking_required": true,
    "price_ranges": ["medium"],
    "tags": ["scenic_view"]
  }
}
```

점수 계산은 다음 요소를 사용한다.

1. 현재 위치 ↔ 코스 시작점 TMAP 왕복 이동 시간
2. 코스 예상 주행 시간
3. 코스 드라이브 적합도
4. 카페 휴식 포인트 수와 카페 조건 일치 여부

`estimated_round_trip_minutes`는 **진입 왕복 시간 + 코스 예상 시간**이다. `estimated_distance_meters`도 같은 기준으로 계산한다.

## 카페

카페 API는 유지한다. 단, 탐색의 주 리소스는 Course다.

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `GET` | `/cafes` | 카페 목록과 조건 필터 |
| `GET` | `/cafes/{cafe_id}` | 카페 상세 |
| `PUT` | `/cafes/{cafe_id}/favorite` | 즐겨찾기 추가 — 구현 예정 |
| `DELETE` | `/cafes/{cafe_id}/favorite` | 즐겨찾기 제거 — 구현 예정 |
| `GET` | `/me/favorites` | 내 즐겨찾기 — 구현 예정 |

## GPS 주행 기록

모든 API는 로그인이 필요하다. 위치 원본은 명시적인 코스 시작 이후에만 업로드한다.

### `POST /drive-records`

TMAP 실행 전에 기록을 생성한다. CoursePath와 NavigationAnchor가 없는 코스는 시작할 수 없다.

```json
{
  "course_id": 1,
  "started_at": "2026-07-15T01:00:00Z"
}
```

### `POST /drive-records/{record_id}/points`

백그라운드 GPS 포인트를 최대 500개까지 순서대로 묶어 전송한다.

```json
{
  "points": [
    {
      "sequence": 0,
      "recorded_at": "2026-07-15T01:00:01Z",
      "latitude": 37.622,
      "longitude": 127.312,
      "accuracy_meters": 8.2,
      "speed_mps": 12.4,
      "heading_degrees": 91.0
    }
  ]
}
```

서버는 각 GPS 포인트와 CoursePath의 최소 거리를 함께 저장한다.

### `POST /drive-records/{record_id}/complete`

```json
{"completed_at": "2026-07-15T03:05:00Z"}
```

완료 시 서버가 다음을 계산한다.

- 실제 이동 거리와 소요 시간
- 코스 기준 시간 대비 `baseline_delta_seconds`
- CoursePath 통과율
- 모든 NavigationAnchor 통과 여부
- 랭킹 반영 가능 여부

기본 검증 기준은 GPS 정확도 50m 이하, Path 통과율 80% 이상, 모든 Anchor 통과다.

### 기록 조회

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `GET` | `/drive-records/{record_id}` | 내 단일 기록 조회 |
| `GET` | `/drive-records?page=1&size=20` | 내 기록 목록 조회 |
| `GET` | `/me/drive-records?page=1&size=20` | 내 기록 목록 호환 경로 |

## 일일 추천·랭킹·소셜 API

아래 API는 전체 구조에 포함되며 다음 개발 단계에서 구현한다.

- `GET /daily-courses`
- `GET /rankings/courses/{course_id}`
- `PUT /cafes/{cafe_id}/favorite`
- `DELETE /cafes/{cafe_id}/favorite`
- `GET /me/favorites`
- `GET/POST /posts`, `POST /posts/{id}/comments`, `PUT /posts/{id}/like`
- `GET/POST /crews`, `POST /crews/{id}/join`, `POST /crews/{id}/invitations`
- `GET/POST /crews/{id}/courses`, `GET /crews/{id}/rankings`
- `GET/PATCH /me/profile`, `GET/POST /me/vehicles`

## 이전 API와 호환성

| 이전 계약 | 변경 계약 | 영향 |
| --- | --- | --- |
| `max_duration_minutes` | `duration_minutes` | 클라이언트 Query 변경 필요 |
| `summary` | `description` | 코스 상세·목록 모델 변경 필요 |
| `waypoints` | `path`, `path_points` | 지도 구현 변경 필요 |
| `recommendation_weight` | `stop_order` | 카페 표시 순서 기준 변경 |
| 카페 중심 추천 | 코스 중심 추천 | 추천 결과 소비 방식 변경 |
| 시작점까지만 TMAP 계산 | 외부 TMAP에 전체 핵심 Anchor 전달 | Flutter TMAP 실행 방식 변경 |
| GPS API 미구현 | GPS 배치 업로드·완주 검증 구현 | 백그라운드 위치 권한 필수 |

Swagger 문서는 개발 서버의 `/docs`, OpenAPI JSON은 `/api/v1/openapi.json`에서 확인한다.
