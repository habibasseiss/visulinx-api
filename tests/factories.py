import factory
import factory.fuzzy

from fast_zero.models import Todo, TodoState, User


class UserFactory(factory.Factory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f'test{n}@test.com')
    password = factory.Sequence(lambda n: f'test{n}@test.com')


class TodoFactory(factory.Factory):
    class Meta:
        model = Todo

    title = factory.Faker('text')
    description = factory.Faker('text')
    state = factory.fuzzy.FuzzyChoice(TodoState)
    user_id = factory.Faker('uuid4')
