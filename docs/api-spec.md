# MVP REST API 명세 초안

기본 URL은 `/api/v1`이다. 보호된 API는 `Authorization: Bearer <access_token>` 헤더가 필요하다. 모든 시간은 ISO 8601 UTC로 교환한다.

## 인증

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `POST` | `/auth/social/login` | 카카오·구글 ID 토큰 검증 후 자체 JWT 발급 |
| `POST` | `/auth/refresh` | Refresh Token으로 Access Token 재발급 |
| `POST` | `/auth/logout` | 현재 세션 폐기 |
| `GET` | `/me` | 내 프로필과 연결된 로그인 제공자 조회 |
| `POST` | `/me/identities` | 다른 소셜 계정 연결 |
| `POST` | `/me/consents` | 위치정보·약관 동의 기록 |

`POST /auth/social/login` 요청 예시:

```json
{
  "provider": "kakao",
  "provider_credential": "provider-issued-token",
  "device_name": "Android"
}
```

`provider_credential`에는 구글 로그인 시 ID Token, 카카오 로그인 시 Access Token을 전달한다.

## 카페와 코스

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `GET` | `/cafes` | 지역·태그·주차·가격대 필터 카페 목록 |
| `GET` | `/cafes/{cafe_id}` | 카페 상세, 이미지, 태그, 연결 코스 |
| `GET` | `/courses` | 지역·분위기·소요시간 필터 코스 목록 |
| `GET` | `/courses/{course_id}` | 코스 상세와 경유지·연결 카페 |
| `PUT` | `/cafes/{cafe_id}/favorite` | 카페 즐겨찾기 추가 |
| `DELETE` | `/cafes/{cafe_id}/favorite` | 카페 즐겨찾기 제거 |
| `GET` | `/me/favorites` | 내 즐겨찾기 목록 |

`GET /cafes` 주요 쿼리: `region`, `latitude`, `longitude`, `radius_km`, `tag`, `parking`, `price_range`, `page`, `size`.

## 추천

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `POST` | `/recommendations` | 위치·시간·조건에 맞는 코스와 카페 추천 |
| `GET` | `/recommendations/{request_id}` | 저장된 추천 결과 재조회 |

요청 예시:

```json
{
  "origin": { "latitude": 37.5665, "longitude": 126.9780 },
  "round_trip_minutes": 180,
  "moods": ["riverside", "quiet"],
  "filters": {
    "parking_required": true,
    "price_ranges": ["medium"],
    "tags": ["scenic_view"]
  }
}
```

응답의 각 후보에는 `course`, `cafe`, `estimated_round_trip_minutes`, `estimated_distance_meters`, `score`, `score_breakdown`, `tmap_navigation`을 포함한다. 점수의 세부 가중치는 내부 운영 정보이므로 사용자 응답에는 사람이 이해할 수 있는 추천 이유를 별도로 제공한다.

## GPS 기록 및 랭킹

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `POST` | `/drive-records` | 기록 시작 |
| `POST` | `/drive-records/{record_id}/points` | GPS 포인트 묶음 업로드 |
| `POST` | `/drive-records/{record_id}/complete` | 기록 종료·요약값 확정 |
| `GET` | `/me/drive-records` | 내 기록 목록 |
| `GET` | `/drive-records/{record_id}` | 내 기록 상세 |
| `GET` | `/rankings/courses` | 코스별 이용·완주 기준 랭킹 |

GPS 포인트는 개별 요청이 아니라 10~30개 단위 배열로 업로드한다. 서버는 속도 이상치·시간 역전·좌표 오류를 검증하고, 랭킹은 완주 수와 이용 수만 사용한다.

## 리뷰

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `GET` | `/cafes/{cafe_id}/reviews` | 자체 작성 리뷰 목록 |
| `POST` | `/cafes/{cafe_id}/reviews` | 리뷰 작성 |
| `PATCH` | `/reviews/{review_id}` | 내 리뷰 수정 |
| `DELETE` | `/reviews/{review_id}` | 내 리뷰 삭제 |

## 공통 응답 규칙

- 목록 응답은 `items`, `page`, `size`, `total`을 반환한다.
- 오류는 `code`, `message`, `details`, `request_id`를 반환한다.
- 외부 지도·경로 제공자 오류는 내부 오류 코드로 변환하고 제공자 토큰·응답 원문을 클라이언트에 노출하지 않는다.
