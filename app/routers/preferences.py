from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Preference, User
from app.schemas import PreferencesList, PreferencesPublic
from app.security import get_current_user

router = APIRouter(prefix='/preferences', tags=['preferences'])

DbSession = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# Routes
@router.get('/', response_model=PreferencesList)
def list_settings(session: DbSession, user: CurrentUser):
    preferences = session.scalars(select(Preference)).all()
    return {
        'preferences': [
            PreferencesPublic.model_validate(p) for p in preferences
        ]
    }


@router.put('/', response_model=PreferencesList)
def update_preferences(
    request: PreferencesList,
    session: DbSession,
    user: CurrentUser,
):
    # Map the incoming preferences by key for quick lookup
    incoming_preferences = {
        pref.key: pref.value for pref in request.preferences
    }

    # Fetch existing preferences from the database that match the incoming keys
    existing_preferences = list(
        session.scalars(
            select(Preference).where(
                Preference.key.in_(incoming_preferences.keys())
            )
        ).all()
    )

    # Update values for existing preferences
    updated_keys = set()
    for pref in existing_preferences:
        if pref.key in incoming_preferences:
            pref.value = incoming_preferences[pref.key]
            updated_keys.add(pref.key)

    # Create new preferences for keys that were not updated
    new_preferences = [
        Preference(key=key, value=value)  # type: ignore
        for key, value in incoming_preferences.items()
        if key not in updated_keys
    ]
    session.add_all(new_preferences)

    # Commit all changes at once
    session.commit()

    # Refresh all preferences (both updated and new)
    all_preferences = existing_preferences + new_preferences
    for pref in all_preferences:
        session.refresh(pref)

    # Prepare the response
    return {
        'preferences': [
            PreferencesPublic(
                key=p.key,
                value=p.value,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in all_preferences
        ]
    }
