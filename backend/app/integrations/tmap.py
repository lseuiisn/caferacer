from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import get_settings

TMAP_API_BASE_URL = "https://apis.openapi.sk.com/tmap"


class TmapError(Exception):
    """Raised when TMAP cannot serve a valid response to the application."""


@dataclass(frozen=True)
class GeocodedAddress:
    latitude: float
    longitude: float
    matched_address: str | None


@dataclass(frozen=True)
class RouteEstimate:
    distance_meters: int
    duration_seconds: int
    taxi_fare: int | None


class TmapClient:
    """TMAP REST client.

    TMAP response data must not be persisted beyond the provider's allowed retention period.
    This client therefore returns only in-memory values; persistence decisions stay in callers.
    """

    def __init__(self, app_key: str | None = None) -> None:
        self._app_key = app_key or get_settings().tmap_app_key

    def _headers(self) -> dict[str, str]:
        if not self._app_key:
            raise TmapError("TMAP_APP_KEY is not configured")
        return {"appKey": self._app_key}

    async def geocode_full_address(self, address: str) -> GeocodedAddress:
        try:
            async with httpx.AsyncClient(base_url=TMAP_API_BASE_URL, timeout=10.0) as client:
                response = await client.get(
                    "/geo/fullAddrGeo",
                    headers=self._headers(),
                    params={
                        "version": "1",
                        "format": "json",
                        "coordType": "WGS84GEO",
                        "fullAddr": address,
                    },
                )
            response.raise_for_status()
            payload = response.json()
            coordinate = ((payload.get("coordinateInfo") or {}).get("coordinate") or [None])[0]
            if not coordinate:
                raise TmapError("No coordinates returned for address")
            latitude = coordinate.get("newLat") or coordinate.get("latEntr")
            longitude = coordinate.get("newLon") or coordinate.get("lonEntr")
            if latitude is None or longitude is None:
                raise TmapError("TMAP response does not contain WGS84 coordinates")
            return GeocodedAddress(
                latitude=float(latitude),
                longitude=float(longitude),
                matched_address=coordinate.get("fullAddress") or coordinate.get("address"),
            )
        except httpx.HTTPStatusError as error:
            raise TmapError(f"TMAP geocoding returned HTTP {error.response.status_code}") from error
        except (httpx.HTTPError, ValueError, TypeError, IndexError) as error:
            raise TmapError("TMAP geocoding request failed") from error

    async def estimate_car_route(
        self,
        *,
        start_latitude: float,
        start_longitude: float,
        end_latitude: float,
        end_longitude: float,
        start_name: str = "출발지",
        end_name: str = "도착지",
    ) -> RouteEstimate:
        body = {
            "startX": str(start_longitude),
            "startY": str(start_latitude),
            "endX": str(end_longitude),
            "endY": str(end_latitude),
            "startName": start_name,
            "endName": end_name,
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO",
            "searchOption": "0",
        }
        try:
            async with httpx.AsyncClient(base_url=TMAP_API_BASE_URL, timeout=15.0) as client:
                response = await client.post(
                    "/routes",
                    headers={**self._headers(), "Content-Type": "application/json"},
                    params={"version": "1", "format": "json"},
                    json=body,
                )
            response.raise_for_status()
            features = response.json().get("features") or []
            properties = next(
                (feature.get("properties", {}) for feature in features if feature.get("geometry", {}).get("type") == "Point"),
                {},
            )
            distance = properties.get("totalDistance")
            duration = properties.get("totalTime")
            if distance is None or duration is None:
                raise TmapError("TMAP route response does not contain a route summary")
            fare = properties.get("taxiFare")
            return RouteEstimate(int(distance), int(duration), int(fare) if fare is not None else None)
        except httpx.HTTPStatusError as error:
            raise TmapError(f"TMAP route request returned HTTP {error.response.status_code}") from error
        except (httpx.HTTPError, ValueError, TypeError) as error:
            raise TmapError("TMAP route request failed") from error
