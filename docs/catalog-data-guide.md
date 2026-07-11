# 카페·코스 초기 데이터 입력 가이드

## 원칙

초기 20개 카페는 자동 크롤링 결과를 곧바로 공개하지 않는다. 카페의 공식 채널 또는 공공 데이터에서 수집한 값을 운영자가 확인한 뒤 `backend/data/catalog.json`에 입력한다.

사진과 타사 리뷰·평점은 해당 콘텐츠를 서비스에 재사용할 권한이 확인되기 전에는 입력하지 않는다.

## 입력 순서

1. `backend/data/catalog.template.json`을 복사해 `backend/data/catalog.json`으로 만든다.
2. 예시 객체를 실제로 검수한 서울·경기도 카페 20개로 교체한다.
3. 모든 카페에 공식 출처 URL과 이용·저장 권한이 확인된 위·경도를 입력한다. TMAP 지오코딩으로 검증한 응답은 약관상 영구 저장용 원천으로 사용하지 않는다.
4. 코스에는 실제 카페 이름과 정확히 같은 `cafe_names` 값을 사용한다.
5. 기본 태그를 생성하고 데이터를 불러온다.

```powershell
cd "C:\Users\ww720\OneDrive\문서\카페 드라이브 앱 개발\backend"
.\.venv\Scripts\python.exe scripts\seed_catalog.py --path data\catalog.json
```

## 지원 태그

| 코드 | 의미 |
| --- | --- |
| `riverside` | 강변 뷰 |
| `ocean_view` | 오션뷰 |
| `city_view` | 도시 뷰 |
| `quiet` | 조용한 분위기 |
| `large_space` | 대형 카페 |
| `pet_friendly` | 반려동물 동반 |
| `kids_friendly` | 키즈 프렌들리 |
| `scenic_drive` | 경치 좋은 드라이브 |

`price_range`은 `low`, `medium`, `high` 중 하나를 사용한다.
