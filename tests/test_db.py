from sqlalchemy import select

from fast_zero.models import Todo, User


def test_create_user(session):
    new_user = User(password='secret', email='teste@test.com')
    session.add(new_user)
    session.commit()

    user = session.scalar(select(User).where(User.email == 'teste@test.com'))

    assert user.email == 'teste@test.com'


def test_create_todo(session, user: User):
    todo = Todo(
        title='Test Todo',
        description='Test Desc',
        state='draft',
        user_id=user.id,
    )

    session.add(todo)
    session.commit()
    session.refresh(todo)

    user = session.scalar(select(User).where(User.id == user.id))

    assert todo in user.todos
