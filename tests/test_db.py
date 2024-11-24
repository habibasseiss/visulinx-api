from sqlalchemy.orm import Session

from app.models import User


def test_user_creation(session: Session):
    # Create a new user
    user = User(  # type: ignore
        email='test@example.com',
        password='securepassword',
    )
    session.add(user)
    session.commit()

    # Verify user is persisted
    queried_user = (
        session.query(User).filter_by(email='test@example.com').first()
    )
    assert queried_user is not None
    assert queried_user.email == 'test@example.com'
