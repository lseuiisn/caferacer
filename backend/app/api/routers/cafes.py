from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession
from app.repositories.catalog import CatalogRepository
from app.schemas.catalog import CafeDetail, CafeListItem, CafePage, PageMeta

router = APIRouter(prefix="/cafes", tags=["cafes"])
repository = CatalogRepository()


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
