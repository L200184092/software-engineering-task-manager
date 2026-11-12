import sqlite3

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from .category_repository import CategoryRepository
from .category_services import CategoryService
from .database import get_connection
from .models import Task, User
from .repository import TaskRepository
from .services import TaskService
from .user_repository import UserRepository

app = FastAPI(
    title="Software Engineering Task Manager API",
    description="REST API untuk mengelola tugas menggunakan SQLite dengan JWT.",
    version="1.1.0",
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)

bearer_scheme = HTTPBearer(auto_error=False)


def get_task_service() -> TaskService:
    return TaskService(repository=TaskRepository())


def get_user_repository() -> UserRepository:
    return UserRepository()


def get_category_service() -> CategoryService:
    return CategoryService(repository=CategoryRepository())


class RegisterRequest(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_.-]+$",
    )
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    priority: str = "Medium"
    due_date: str | None = None
    category_id: int | None = Field(default=None, ge=1)


class TaskUpdate(BaseModel):
    """Data lengkap yang diperlukan untuk mengganti tugas."""

    title: str = Field(min_length=1, max_length=200)
    description: str
    priority: str
    due_date: str | None
    category_id: int | None = Field(default=None, ge=1)


class TaskPatch(BaseModel):
    """Data untuk memperbarui sebagian field tugas."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: str | None = None
    due_date: str | None = None
    category_id: int | None = Field(default=None, ge=1)


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CategoryUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CategoryResponse(BaseModel):
    id: int
    name: str


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    completed: bool
    priority: str
    due_date: str | None
    category_id: int | None
    deadline_status: str


def to_task_response(task: Task, service: TaskService) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        completed=task.completed,
        priority=task.priority,
        due_date=task.due_date,
        category_id=task.category_id,
        deadline_status=service.get_deadline_status(task),
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    users: UserRepository = Depends(get_user_repository),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    # A token for a deleted/nonexistent account is not accepted.
    with get_connection(users.db_path) as connection:
        row = connection.execute(
            "SELECT id, username, email, password_hash FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return User(
        id=row["id"],
        username=row["username"],
        email=row["email"],
        password_hash=row["password_hash"],
    )


@app.get("/")
def root():
    return {"message": "Task Manager API is running", "docs": "/docs"}


@app.post(
    "/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(
    payload: RegisterRequest, users: UserRepository = Depends(get_user_repository)
):
    user = User(
        username=payload.username.strip(),
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
    )
    try:
        created = users.create(user)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409, detail="Username or email already registered"
        ) from exc
    return UserResponse(id=created.id, username=created.username, email=created.email)


@app.post("/auth/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    payload: LoginRequest,
    users: UserRepository = Depends(get_user_repository),
):
    user = users.get_by_username(payload.username)

    if user is None or not verify_password(
        payload.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(access_token=create_access_token(str(user.id)))


@app.get("/categories", response_model=list[CategoryResponse])
def list_categories(
    user: User = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
):
    categories = service.get_categories(user.id)
    return [
        CategoryResponse(id=category.id, name=category.name) for category in categories
    ]


@app.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    payload: CategoryCreate,
    user: User = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
):
    try:
        category = service.create_category(payload.name, user.id)
    except ValueError as exc:
        message = str(exc)
        code = 409 if "sudah digunakan" in message.lower() else 422
        raise HTTPException(status_code=code, detail=message) from exc

    return CategoryResponse(id=category.id, name=category.name)


@app.patch("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    user: User = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
):
    try:
        category = service.update_category(category_id, user.id, payload.name)
    except ValueError as exc:
        message = str(exc)
        code = (
            404
            if "tidak ditemukan" in message.lower()
            else (409 if "sudah digunakan" in message.lower() else 422)
        )
        raise HTTPException(status_code=code, detail=message) from exc

    return CategoryResponse(id=category.id, name=category.name)


@app.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_category(
    category_id: int,
    user: User = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
):
    try:
        service.delete_category(category_id, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/tasks", response_model=list[TaskResponse])
def list_tasks(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=200),
    completed: bool | None = Query(default=None),
    priority: str | None = Query(default=None, max_length=20),
    sort_by: str = Query(default="id"),
    sort_order: str = Query(default="asc"),
    due_from: str | None = Query(default=None),
    due_to: str | None = Query(default=None),
    category_id: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    if search is not None and not search.strip():
        raise HTTPException(
            status_code=422,
            detail="Parameter search tidak boleh hanya berisi spasi.",
        )

    try:
        due_from = service.validate_due_date(due_from)
        due_to = service.validate_due_date(due_to)

        if due_from and due_to and due_from > due_to:
            raise ValueError(
                "Tanggal awal deadline tidak boleh melebihi tanggal akhir."
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if priority is not None:
        try:
            priority = service.validate_priority(priority)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    if category_id is not None:
        if category_id == "uncategorized":
            category_filter = "uncategorized"
        else:
            try:
                category_filter = int(category_id)
                if category_filter < 1:
                    raise ValueError
            except ValueError as exc:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "category_id harus berupa ID kategori positif "
                        "atau 'uncategorized'."
                    ),
                ) from exc
    else:
        category_filter = None

    allowed_sort_fields = {
        "id",
        "created_at",
        "title",
        "priority",
        "due_date",
    }

    if sort_by not in allowed_sort_fields:
        raise HTTPException(
            status_code=422,
            detail="Kolom pengurutan tidak valid.",
        )

    sort_order = sort_order.lower()

    if sort_order not in {"asc", "desc"}:
        raise HTTPException(
            status_code=422,
            detail="Arah pengurutan harus 'asc' atau 'desc'.",
        )

    tasks = service.repository.get_all_for_user(
        user.id,
        limit=limit,
        offset=offset,
        search=search,
        completed=completed,
        priority=priority,
        sort_by=sort_by,
        sort_order=sort_order,
        due_from=due_from,
        due_to=due_to,
        category_id=category_filter,
    )

    return [to_task_response(task, service) for task in tasks]


@app.get("/tasks/statistics")
def get_task_statistics(
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    return service.get_user_task_statistics(user.id)


@app.get("/tasks/dashboard")
def get_task_dashboard(
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    return service.get_user_task_dashboard(user.id)


@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
    category_service: CategoryService = Depends(get_category_service),
):
    try:
        title = payload.title.strip()
        description = payload.description.strip()
        if not title:
            raise ValueError("Judul tugas tidak boleh kosong.")
        priority = service.validate_priority(payload.priority)
        due_date = service.validate_due_date(payload.due_date)
        if payload.category_id is not None:
            category = category_service.get_category(payload.category_id, user.id)
            if category is None:
                raise HTTPException(status_code=404, detail="Category not found")
        task = service.repository.create_for_user(
            Task(
                title=title,
                description=description,
                priority=priority,
                due_date=due_date,
                category_id=payload.category_id,
            ),
            user.id,
        )

        return to_task_response(task, service)

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    task = service.repository.get_for_user(task_id, user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return to_task_response(task, service)


@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
    category_service: CategoryService = Depends(get_category_service),
):
    try:
        title = payload.title.strip()
        description = payload.description.strip()
        if not title:
            raise ValueError("Judul tugas tidak boleh kosong.")
        priority = service.validate_priority(payload.priority or "Medium")
        due_date = service.validate_due_date(payload.due_date)
        if payload.category_id is not None:
            category = category_service.get_category(payload.category_id, user.id)
            if category is None:
                raise HTTPException(status_code=404, detail="Category not found")
        updated = service.repository.update_for_user(
            task_id,
            user.id,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            category_id=payload.category_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    task = service.repository.get_for_user(task_id, user.id)
    return to_task_response(task, service)


@app.patch("/tasks/{task_id}", response_model=TaskResponse)
def patch_task(
    task_id: int,
    payload: TaskPatch,
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
    category_service: CategoryService = Depends(get_category_service),
):
    fields = payload.model_dump(exclude_unset=True)

    if not fields:
        raise HTTPException(
            status_code=422,
            detail="Setidaknya satu field harus dikirim.",
        )

    try:
        if "title" in fields:
            if fields["title"] is None:
                raise ValueError("Judul tugas tidak boleh null.")

            fields["title"] = fields["title"].strip()
            if not fields["title"]:
                raise ValueError("Judul tugas tidak boleh kosong.")

        if "description" in fields:
            if fields["description"] is None:
                raise ValueError("Deskripsi tidak boleh null.")

            fields["description"] = fields["description"].strip()

        if "priority" in fields:
            if fields["priority"] is None:
                raise ValueError("Prioritas tidak boleh null.")

            fields["priority"] = service.validate_priority(fields["priority"])

        if "due_date" in fields:
            fields["due_date"] = service.validate_due_date(fields["due_date"])

        if "category_id" in fields and fields["category_id"] is not None:
            category = category_service.get_category(fields["category_id"], user.id)
            if category is None:
                raise HTTPException(status_code=404, detail="Category not found")

        updated = service.repository.update_fields_for_user(
            task_id,
            user.id,
            fields,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    task = service.repository.get_for_user(task_id, user.id)
    return to_task_response(task, service)


@app.patch("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    if not service.repository.complete_for_user(task_id, user.id):
        raise HTTPException(status_code=404, detail="Task not found")
    task = service.repository.get_for_user(task_id, user.id)
    return to_task_response(task, service)


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    if not service.repository.delete_for_user(task_id, user.id):
        raise HTTPException(status_code=404, detail="Task not found")
