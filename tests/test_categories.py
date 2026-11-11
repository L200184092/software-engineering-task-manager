import pytest

from task_manager.auth import hash_password
from task_manager.category_repository import CategoryRepository
from task_manager.category_services import CategoryService
from task_manager.models import User
from task_manager.user_repository import UserRepository


@pytest.fixture
def category_service(tmp_path):
    db_path = tmp_path / "test_categories.db"

    user_repository = UserRepository(db_path)

    user_repository.create(
        User(
            username="user_one",
            email="user_one@example.com",
            password_hash=hash_password("Password123!"),
        )
    )

    user_repository.create(
        User(
            username="user_two",
            email="user_two@example.com",
            password_hash=hash_password("Password123!"),
        )
    )

    repository = CategoryRepository(db_path)
    return CategoryService(repository)


def test_create_category(category_service):
    category = category_service.create_category("Work", user_id=1)

    assert category.id is not None
    assert category.name == "Work"
    assert category.user_id == 1


def test_create_category_trims_whitespace(category_service):
    category = category_service.create_category("  Personal  ", user_id=1)

    assert category.name == "Personal"


def test_create_category_rejects_empty_name(category_service):
    with pytest.raises(ValueError, match="tidak boleh kosong"):
        category_service.create_category("   ", user_id=1)


def test_create_duplicate_category(category_service):
    category_service.create_category("Work", user_id=1)

    with pytest.raises(ValueError, match="sudah digunakan"):
        category_service.create_category("Work", user_id=1)


def test_same_category_name_allowed_for_different_users(category_service):
    first = category_service.create_category("Work", user_id=1)
    second = category_service.create_category("Work", user_id=2)

    assert first.id != second.id
    assert first.user_id == 1
    assert second.user_id == 2


def test_get_categories_only_returns_own_categories(category_service):
    category_service.create_category("Work", user_id=1)
    category_service.create_category("Personal", user_id=1)
    category_service.create_category("Finance", user_id=2)

    categories = category_service.get_categories(user_id=1)

    assert len(categories) == 2
    assert {category.name for category in categories} == {
        "Work",
        "Personal",
    }


def test_get_category_rejects_other_users(category_service):
    category = category_service.create_category("Work", user_id=1)

    result = category_service.get_category(
        category_id=category.id,
        user_id=2,
    )

    assert result is None


def test_update_category(category_service):
    category = category_service.create_category("Work", user_id=1)

    updated = category_service.update_category(
        category_id=category.id,
        user_id=1,
        name="Business",
    )

    assert updated.id == category.id
    assert updated.name == "Business"


def test_update_category_rejects_duplicate_name(category_service):
    category_service.create_category("Work", user_id=1)
    second = category_service.create_category("Personal", user_id=1)

    with pytest.raises(ValueError, match="sudah digunakan"):
        category_service.update_category(
            category_id=second.id,
            user_id=1,
            name="Work",
        )


def test_update_category_rejects_other_users(category_service):
    category = category_service.create_category("Work", user_id=1)

    with pytest.raises(ValueError, match="tidak ditemukan"):
        category_service.update_category(
            category_id=category.id,
            user_id=2,
            name="Business",
        )


def test_delete_category(category_service):
    category = category_service.create_category("Work", user_id=1)

    result = category_service.delete_category(
        category_id=category.id,
        user_id=1,
    )

    assert result is True
    assert category_service.get_category(category.id, user_id=1) is None


def test_delete_category_rejects_other_users(category_service):
    category = category_service.create_category("Work", user_id=1)

    with pytest.raises(ValueError, match="tidak ditemukan"):
        category_service.delete_category(
            category_id=category.id,
            user_id=2,
        )

    assert category_service.get_category(category.id, user_id=1) is not None
