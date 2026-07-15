from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.integrations.tmap import TmapClient, TmapError
from app.schemas.recommendations import Coordinate

router = APIRouter(prefix="/places", tags=["places"])


class PlaceResponse(BaseModel):
    name: str
    address: str | None
    coordinate: Coordinate


@router.get("/search", response_model=list[PlaceResponse])
async def search_places(
    current_user: CurrentUser,
    q: str = Query(min_length=2, max_length=100),
    size: int = Query(default=10, ge=1, le=20),
) -> list[PlaceResponse]:
    try:
        items = await TmapClient().search_places(q, count=size)
    except TmapError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return [PlaceResponse(
        name=item.name,
        address=item.address,
        coordinate=Coordinate(latitude=item.latitude, longitude=item.longitude),
    ) for item in items]
