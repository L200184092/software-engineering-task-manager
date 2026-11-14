import pytest
from fastapi.testclient import TestClient

from task_manager.api import (
    app,
    get_category_service,
    get_task_service,
    get_user_repository,
    limiter,
)
from task_manager.category_repository import CategoryRepository
from task_manager.category_services import CategoryService
from task_manager.database import init_db
from task_manager.repository import TaskRepository
from task_manager.services import TaskService
from task_manager.user_repository import UserRepository


@pytest.fixture
def client(tmp_path):
    limiter.reset()

    db_path = tmp_path / "test_tasks.db"
    init_db(db_path)

    service = TaskService(repository=TaskRepository(db_path=db_path))
    categories = CategoryService(repository=CategoryRepository(db_path=db_path))
    users = UserRepository(db_path=db_path)

    app.dependency_overrides[get_task_service] = lambda: service
    app.dependency_overrides[get_category_service] = lambda: categories
    app.dependency_overrides[get_user_repository] = lambda: users

    try:
        with TestClient(app) as test_client:
            test_client.db_path = db_path
            yield test_client
    finally:
        app.dependency_overrides.clear()
