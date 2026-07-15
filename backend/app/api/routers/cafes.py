from typing import Annotated

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.models.catalog import Cafe
from app.models.social import Favorite
from app.integrations.tmap import TmapClient, TmapError
from app.repositories.catalog import CatalogRepository
from app.schemas.catalog import CafeDetail, CafeListItem, CafePage, PageMeta
from app.schemas.recommendations import Coordinate

router = APIRouter(prefix="/cafes", tags=["cafes"])
me_router = APIRouter(prefix="/me", tags=["favorites"])
repository = CatalogRepository()


class CafeNavigationRequest(BaseModel):
    origin: Coordinate


class CafeNavigationResponse(BaseModel):
    distance_meters: int
    duration_seconds: int


def cafe_response(cafe, tags: list[str], thumbnail_url: str | None) -> CafeListItem:
    return CafeListItem(
        id=cafe.id,
        name=cafe.name,
        address=cafe.address,
        latitude=cafe.latitude,
        longitude=cafe.longitude,
        price_range=cafe.price_range,
        parking_available=cafe.parking_available,
        tags=tags,
        thumbnail_url=thumbnail_url,
    )


@router.get("", response_model=CafePage)
def list_cafes(
    db: DbSession,
    tags: Annotated[list[str] | None, Query(description="모두 만족해야 하는 태그 코드")] = None,
    parking: bool | None = None,
    price_ranges: Annotated[list[str] | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> CafePage:
    cafes, total = repository.list_cafes(
        db, tags=tags, parking=parking, price_ranges=price_ranges, page=page, size=size
    )
    cafe_ids = [cafe.id for cafe in cafes]
    tag_map = repository.cafe_tags(db, cafe_ids)
    image_map = repository.cafe_images(db, cafe_ids)
    return CafePage(
        items=[
            cafe_response(cafe, tag_map[cafe.id], image_map[cafe.id][0].image_url if image_map[cafe.id] else None)
            for cafe in cafes
        ],
        meta=PageMeta(page=page, size=size, total=total),
    )


@router.get("/{cafe_id}", response_model=CafeDetail)
def get_cafe(cafe_id: int, db: DbSession) -> CafeDetail:
    cafe = repository.get_cafe(db, cafe_id)
    if cafe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cafe not found")
    tags = repository.cafe_tags(db, [cafe.id])[cafe.id]
    images = repository.cafe_images(db, [cafe.id])[cafe.id]
    return CafeDetail(
        **cafe_response(cafe, tags, images[0].image_url if images else None).model_dump(),
        phone_number=cafe.phone_number,
        business_hours=cafe.business_hours,
        verified_at=cafe.verified_at,
        images=images,
    )


@router.post("/{cafe_id}/navigation", response_model=CafeNavigationResponse)
async def cafe_navigation(
    cafe_id: int,
    payload: CafeNavigationRequest,
    db: DbSession,
) -> CafeNavigationResponse:
    cafe = repository.get_cafe(db, cafe_id)
    if cafe is None:
        raise HTTPException(status_code=404, detail="Cafe not found")
    try:
        route = await TmapClient().estimate_car_route(
            start_latitude=payload.origin.latitude,
            start_longitude=payload.origin.longitude,
            end_latitude=float(cafe.latitude),
            end_longitude=float(cafe.longitude),
            start_name="현재 위치",
            end_name=cafe.name,
        )
    except TmapError as error:
        raise HTTPException(status_code=502, detail="TMAP navigation is unavailable") from error
    return CafeNavigationResponse(
        distance_meters=route.distance_meters,
        duration_seconds=route.duration_seconds,
    )


@router.put("/{cafe_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def add_favorite(cafe_id: int, current_user: CurrentUser, db: DbSession) -> None:
    if repository.get_cafe(db, cafe_id) is None:
        raise HTTPException(status_code=404, detail="Cafe not found")
    key = {"user_id": current_user.id, "cafe_id": cafe_id}
    if db.get(Favorite, key) is None:
        db.add(
            Favorite(
                **key,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()


@router.delete("/{cafe_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(cafe_id: int, current_user: CurrentUser, db: DbSession) -> None:
    favorite = db.get(Favorite, {"user_id": current_user.id, "cafe_id": cafe_id})
    if favorite is not None:
        db.delete(favorite)
        db.commit()


@me_router.get("/favorites", response_model=list[CafeListItem])
def list_favorites(current_user: CurrentUser, db: DbSession) -> list[CafeListItem]:
    cafes = list(
        db.scalars(
            select(Cafe)
            .join(Favorite, Favorite.cafe_id == Cafe.id)
            .where(Favorite.user_id == current_user.id, Cafe.is_active.is_(True))
            .order_by(Favorite.created_at.desc())
        )
    )
    ids = [cafe.id for cafe in cafes]
    tags = repository.cafe_tags(db, ids)
    images = repository.cafe_images(db, ids)
    return [
        cafe_response(
            cafe,
            tags[cafe.id],
            images[cafe.id][0].image_url if images[cafe.id] else None,
        )
        for cafe in cafes
    ]
