import pytest


@pytest.fixture(autouse=True)
def setup_permissions(db):
    """Automatically set up groups and permissions for all tests."""
    from accounts.permissions import setup_groups_and_permissions
    setup_groups_and_permissions()


@pytest.fixture
def user_factory(db):
    """Factory fixture for creating users."""
    from django.contrib.auth import get_user_model
    from accounts.permissions import assign_user_to_group
    
    User = get_user_model()
    
    def create_user(**kwargs):
        defaults = {
            'password': 'pass12345',
            'role': 'USER',
        }
        defaults.update(kwargs)
        password = defaults.pop('password')
        user = User.objects.create_user(**defaults)
        user.set_password(password)
        user.save()
        assign_user_to_group(user)
        return user
    return create_user


@pytest.fixture
def superadmin_user(user_factory):
    """Create a superadmin user."""
    user = user_factory(
        username='superadmin',
        password='pass12345!',
        role='SUPERADMIN',
        must_change_password=False,
        is_staff=True,
        is_superuser=True,
    )
    return user


@pytest.fixture
def admin_user(user_factory):
    """Create an admin user."""
    user = user_factory(
        username='admin1',
        password='pass12345',
        role='ADMIN',
        must_change_password=False,
        is_staff=True,
    )
    return user


@pytest.fixture
def regular_user(user_factory):
    """Create a regular user."""
    return user_factory(
        username='alice',
        email='alice@example.com',
        password='pass12345',
        role='USER',
    )
