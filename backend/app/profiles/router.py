from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.core.database import get_request_db
from app.core.governance import redact_hidden_parameters
from app.profiles.models import KnowledgeProfile, ModelProfile
from app.profiles.schemas import AdminProfileRead, MedicalProfileRead, ProfileCreate, ProfilePatch
from app.profiles.service import create_profile, get_profile, list_profiles, update_profile
from app.users.models import User

router = APIRouter(prefix="/api/v1", tags=["profiles"])
_admin_user = require_role("admin_developer")


def _read(profile: Any, *, admin: bool) -> AdminProfileRead | MedicalProfileRead:
    if admin:
        return AdminProfileRead(
            id=profile.id,
            name=profile.name,
            description=profile.description,
            exposed_to_medical=profile.exposed_to_medical,
            medical_options=profile.medical_options_json,
            technical_config=profile.technical_config_json,
            is_active=profile.is_active,
        )
    return MedicalProfileRead(
        id=profile.id,
        name=profile.name,
        description=profile.description,
        exposed_to_medical=profile.exposed_to_medical,
        medical_options=redact_hidden_parameters(profile.medical_options_json),
    )


def _list_endpoint(model: Any, db: Session, current_user: User):
    admin = current_user.role == "admin_developer"
    return [_read(item, admin=admin) for item in list_profiles(db, model, medical_only=not admin)]


@router.get("/model-profiles", response_model=list[AdminProfileRead | MedicalProfileRead])
def list_model_profiles(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
):
    return _list_endpoint(ModelProfile, db, current_user)


@router.get("/knowledge-profiles", response_model=list[AdminProfileRead | MedicalProfileRead])
def list_knowledge_profiles(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
):
    return _list_endpoint(KnowledgeProfile, db, current_user)


def _create_endpoint(model: Any, payload: ProfileCreate, db: Session, current_user: User):
    try:
        profile = create_profile(db, model, payload, current_user.id)
        db.commit()
        return _read(profile, admin=True)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "conflict", "message": "profile name already exists"}) from exc


@router.post("/model-profiles", response_model=AdminProfileRead, status_code=status.HTTP_201_CREATED)
def create_model_profile(
    payload: ProfileCreate,
    current_user: Annotated[User, Depends(_admin_user)],
    db: Annotated[Session, Depends(get_request_db)],
):
    return _create_endpoint(ModelProfile, payload, db, current_user)


@router.post("/knowledge-profiles", response_model=AdminProfileRead, status_code=status.HTTP_201_CREATED)
def create_knowledge_profile(
    payload: ProfileCreate,
    current_user: Annotated[User, Depends(_admin_user)],
    db: Annotated[Session, Depends(get_request_db)],
):
    return _create_endpoint(KnowledgeProfile, payload, db, current_user)


def _patch_endpoint(model: Any, profile_id: str, payload: ProfilePatch, db: Session, current_user: User):
    profile = get_profile(db, model, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "profile not found"})
    try:
        profile = update_profile(db, model, profile, payload, current_user.id)
        db.commit()
        return _read(profile, admin=True)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "conflict", "message": "profile name already exists"}) from exc


@router.patch("/model-profiles/{profile_id}", response_model=AdminProfileRead)
def patch_model_profile(
    profile_id: str,
    payload: ProfilePatch,
    current_user: Annotated[User, Depends(_admin_user)],
    db: Annotated[Session, Depends(get_request_db)],
):
    return _patch_endpoint(ModelProfile, profile_id, payload, db, current_user)


@router.patch("/knowledge-profiles/{profile_id}", response_model=AdminProfileRead)
def patch_knowledge_profile(
    profile_id: str,
    payload: ProfilePatch,
    current_user: Annotated[User, Depends(_admin_user)],
    db: Annotated[Session, Depends(get_request_db)],
):
    return _patch_endpoint(KnowledgeProfile, profile_id, payload, db, current_user)
