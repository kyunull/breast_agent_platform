from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.core.credentials import CredentialManager
from app.profiles.models import KnowledgeProfile, ModelProfile
from app.profiles.schemas import ProfileCreate, ProfilePatch


def list_profiles[ProfileModel: (ModelProfile, KnowledgeProfile)](
    db: Session,
    model: type[ProfileModel],
    *,
    medical_only: bool,
) -> list[ProfileModel]:
    statement = select(model).order_by(model.name)
    if medical_only:
        statement = statement.where(model.is_active.is_(True), model.exposed_to_medical.is_(True))
    return list(db.scalars(statement))


def get_profile[ProfileModel: (ModelProfile, KnowledgeProfile)](
    db: Session,
    model: type[ProfileModel],
    profile_id: str,
) -> ProfileModel | None:
    return db.get(model, profile_id)


def create_profile[ProfileModel: (ModelProfile, KnowledgeProfile)](
    db: Session,
    model: type[ProfileModel],
    payload: ProfileCreate,
    actor_id: str,
    credential_manager: CredentialManager | None = None,
) -> ProfileModel:
    technical_config = dict(payload.technical_config)
    if model is ModelProfile and payload.api_key:
        if credential_manager is None:
            raise RuntimeError("credential manager is required for model profiles")
        technical_config["api_key_encrypted"] = credential_manager.encrypt_secret(payload.api_key)
    profile = model(
        name=payload.name,
        description=payload.description,
        technical_config_json=technical_config,
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


def update_profile[ProfileModel: (ModelProfile, KnowledgeProfile)](
    db: Session,
    model: type[ProfileModel],
    profile: ProfileModel,
    payload: ProfilePatch,
    actor_id: str,
    credential_manager: CredentialManager | None = None,
) -> ProfileModel:
    changed_fields: list[str] = []
    values = payload.model_dump(exclude_unset=True)
    secret = values.pop("api_key", None)
    for field, value in values.items():
        if model is ModelProfile and field == "technical_config":
            existing_secret = profile.technical_config_json.get("api_key_encrypted")
            value = dict(value)
            if existing_secret:
                value["api_key_encrypted"] = existing_secret
        setattr(profile, field if field not in {"technical_config", "medical_options"} else f"{field}_json", value)
        changed_fields.append(field)
    if model is ModelProfile and secret:
        if credential_manager is None:
            raise RuntimeError("credential manager is required for model profiles")
        config = dict(profile.technical_config_json)
        config["api_key_encrypted"] = credential_manager.encrypt_secret(secret)
        profile.technical_config_json = config
        changed_fields.append("api_key")
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
