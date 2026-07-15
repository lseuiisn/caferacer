from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select, update

from app.api.deps import CurrentUser, DbSession
from app.models.social import UserProfile, UserVehicle
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdate,
    VehicleCreate,
    VehicleResponse,
)

router = APIRouter(prefix="/me", tags=["profile"])


def profile_response(user: CurrentUser, db: DbSession) -> ProfileResponse:
    profile = db.get(UserProfile, user.id)
    vehicles = list(
        db.scalars(
            select(UserVehicle)
            .where(UserVehicle.user_id == user.id)
            .order_by(UserVehicle.is_primary.desc(), UserVehicle.id)
        )
    )
    return ProfileResponse(
        user_id=user.id,
        nickname=user.nickname,
        bio=profile.bio if profile else None,
        profile_image_url=profile.profile_image_url if profile else None,
        connected_accounts=[identity.provider.value for identity in user.identities],
        vehicles=vehicles,
        created_at=user.created_at,
    )


@router.get("/profile", response_model=ProfileResponse)
def get_profile(current_user: CurrentUser, db: DbSession) -> ProfileResponse:
    return profile_response(current_user, db)


@router.patch("/profile", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ProfileResponse:
    values = payload.model_dump(exclude_unset=True)
    if "nickname" in values:
        current_user.nickname = values.pop("nickname")
    profile = db.get(UserProfile, current_user.id)
    if profile is None:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    for key, value in values.items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(current_user)
    return profile_response(current_user, db)


@router.get("/vehicles", response_model=list[VehicleResponse])
def list_vehicles(current_user: CurrentUser, db: DbSession) -> list[UserVehicle]:
    return list(
        db.scalars(
            select(UserVehicle)
            .where(UserVehicle.user_id == current_user.id)
            .order_by(UserVehicle.is_primary.desc(), UserVehicle.id)
        )
    )


@router.post("/vehicles", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    payload: VehicleCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> UserVehicle:
    if payload.is_primary:
        db.execute(
            update(UserVehicle)
            .where(UserVehicle.user_id == current_user.id)
            .values(is_primary=False)
        )
    vehicle = UserVehicle(user_id=current_user.id, **payload.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.delete("/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(vehicle_id: int, current_user: CurrentUser, db: DbSession) -> None:
    vehicle = db.scalar(
        select(UserVehicle).where(
            UserVehicle.id == vehicle_id,
            UserVehicle.user_id == current_user.id,
        )
    )
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    db.delete(vehicle)
    db.commit()
