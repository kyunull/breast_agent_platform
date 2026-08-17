from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.profiles.models import KnowledgeProfile, ModelProfile
from app.profiles.schemas import ProfileCreate, ProfilePatch


ProfileModel = TypeVar("ProfileModel", ModelProfile, KnowledgeProfile)


def list_profiles(
    db: Session,
    model: type[ProfileModel],
    *,
    medical_only: bool,
) -> list[ProfileModel]:
    statement = select(model).order_by(model.name)
    if medical_only:
        statement = statement.where(model.is_active.is_(True), model.exposed_to_medical.is_(True))
    return list(db.scalars(statement))


def get_profile(db: Session, model: type[ProfileModel], profile_id: str) -> ProfileModel | None:
    return db.get(model, profile_id)


def create_profile(
    db: Session,
    model: type[ProfileModel],
    payload: ProfileCreate,
    actor_id: str,
) -> ProfileModel:
    profile = model(
        name=payload.name,
        description=payload.description,
        technical_config_json=payload.technical_config,
        medical_options_json=payload.medical_options,
        exposed_to_medical=payload.exposed_to_medical,
        is_active=payload.is_active,
    )
    db.add(profile)
    db.flush()
    record_audit(
        db,
        actor_id=actor_id,
        action="profile.create",
        entity_type=model.__tablename__,
        entity_id=profile.id,
        metadata={"profile_id": profile.id, "changed_fields": ["name", "description", "exposed_to_medical", "is_active"]},
    )
    return profile


def update_profile(
    db: Session,
    model: type[ProfileModel],
    profile: ProfileModel,
    payload: ProfilePatch,
    actor_id: str,
) -> ProfileModel:
    changed_fields: list[str] = []
    values = payload.model_dump(exclude_unset=True)
    for field, value in values.items():
        setattr(profile, field if field not in {"technical_config", "medical_options"} else f"{field}_json", value)
        changed_fields.append(field)
    if changed_fields:
        record_audit(
            db,
            actor_id=actor_id,
            action="profile.update",
            entity_type=model.__tablename__,
            entity_id=profile.id,
            metadata={"profile_id": profile.id, "changed_fields": changed_fields},
        )
    db.flush()
    return profile
