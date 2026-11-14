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
from .subtask_repository import SubtaskRepository
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
    recurrence: str = "none"


class TaskUpdate(BaseModel):
    """Data lengkap yang diperlukan untuk mengganti tugas."""

    title: str = Field(min_length=1, max_length=200)
    description: str
    priority: str
    due_date: str | None
    category_id: int | None = Field(default=None, ge=1)
    recurrence: str = "none"


class TaskPatch(BaseModel):
    """Data untuk memperbarui sebagian field tugas."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: str | None = None
    due_date: str | None = None
    category_id: int | None = Field(default=None, ge=1)
    recurrence: str | None = None


class SubtaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class SubtaskUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class SubtaskResponse(BaseModel):
    id: int
    task_id: int
    title: str
    completed: bool


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
    recurrence: str
    next_occurrence_created: bool
    deadline_status: str
    subtask_total: int = 0
    subtask_completed: int = 0
    subtask_progress: float = 0.0


def to_task_response(
    task: Task, service: TaskService, user_id: int | None = None
) -> TaskResponse:
    subtask_summary = (
        SubtaskRepository(service.repository.db_path).get_summary(task.id, user_id)
        if user_id is not None and task.id is not None
        else {"subtask_total": 0, "subtask_completed": 0, "subtask_progress": 0.0}
    )
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        completed=task.completed,
        priority=task.priority,
        due_date=task.due_date,
        category_id=task.category_id,
        recurrence=task.recurrence,
        next_occurrence_created=task.next_occurrence_created,
        deadline_status=service.get_deadline_status(task),
        **subtask_summary,
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

    return [to_task_response(task, service, user.id) for task in tasks]


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
        recurrence = service.validate_recurrence(payload.recurrence)
        if recurrence != "none" and due_date is None:
            raise ValueError("Tugas berulang harus memiliki tanggal tenggat.")
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
                recurrence=recurrence,
            ),
            user.id,
        )

        return to_task_response(task, service, user.id)

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
    return to_task_response(task, service, user.id)


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
        recurrence = service.validate_recurrence(payload.recurrence)
        if recurrence != "none" and due_date is None:
            raise ValueError("Tugas berulang harus memiliki tanggal tenggat.")
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
            recurrence=recurrence,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    task = service.repository.get_for_user(task_id, user.id)
    return to_task_response(task, service, user.id)


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

        if "recurrence" in fields:
            if fields["recurrence"] is None:
                raise ValueError("Pengaturan pengulangan tidak boleh null.")
            fields["recurrence"] = service.validate_recurrence(fields["recurrence"])

        current_task = service.repository.get_for_user(task_id, user.id)
        if current_task is not None:
            effective_recurrence = fields.get("recurrence", current_task.recurrence)
            effective_due_date = fields.get("due_date", current_task.due_date)
            if effective_recurrence != "none" and effective_due_date is None:
                raise ValueError("Tugas berulang harus memiliki tanggal tenggat.")

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
    return to_task_response(task, service, user.id)


@app.patch("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    if not service.repository.complete_for_user(task_id, user.id):
        raise HTTPException(status_code=404, detail="Task not found")
    task = service.repository.get_for_user(task_id, user.id)
    return to_task_response(task, service, user.id)


@app.post(
    "/tasks/{task_id}/next-occurrence",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_next_task_occurrence(
    task_id: int,
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    """Create the next recurring task only when explicitly requested."""
    try:
        task = service.create_next_occurrence(task_id, user.id)
    except ValueError as exc:
        message = str(exc)
        code = 404 if message == "Tugas tidak ditemukan." else 422
        raise HTTPException(status_code=code, detail=message) from exc
    return to_task_response(task, service, user.id)


@app.get("/tasks/{task_id}/subtasks", response_model=list[SubtaskResponse])
def list_subtasks(
    task_id: int,
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    subtasks = SubtaskRepository(service.repository.db_path).list_for_task(
        task_id, user.id
    )
    if subtasks is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return [
        SubtaskResponse(
            id=item.id, task_id=item.task_id, title=item.title, completed=item.completed
        )
        for item in subtasks
    ]


@app.post(
    "/tasks/{task_id}/subtasks",
    response_model=SubtaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_subtask(
    task_id: int,
    payload: SubtaskCreate,
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Judul subtask tidak boleh kosong.")
    subtask = SubtaskRepository(service.repository.db_path).create_for_task(
        task_id, user.id, title
    )
    if subtask is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return SubtaskResponse(
        id=subtask.id,
        task_id=subtask.task_id,
        title=subtask.title,
        completed=subtask.completed,
    )


@app.patch("/tasks/{task_id}/subtasks/{subtask_id}", response_model=SubtaskResponse)
def update_subtask(
    task_id: int,
    subtask_id: int,
    payload: SubtaskUpdate,
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Judul subtask tidak boleh kosong.")
    repository = SubtaskRepository(service.repository.db_path)
    if not repository.update_for_user(subtask_id, task_id, user.id, title=title):
        raise HTTPException(status_code=404, detail="Subtask not found")
    subtasks = repository.list_for_task(task_id, user.id)
    subtask = next(item for item in subtasks if item.id == subtask_id)
    return SubtaskResponse(
        id=subtask.id,
        task_id=subtask.task_id,
        title=subtask.title,
        completed=subtask.completed,
    )


@app.patch(
    "/tasks/{task_id}/subtasks/{subtask_id}/complete",
    response_model=SubtaskResponse,
)
def complete_subtask(
    task_id: int,
    subtask_id: int,
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    repository = SubtaskRepository(service.repository.db_path)
    if not repository.complete_for_user(subtask_id, task_id, user.id):
        raise HTTPException(status_code=404, detail="Subtask not found")
    subtasks = repository.list_for_task(task_id, user.id)
    subtask = next(item for item in subtasks if item.id == subtask_id)
    return SubtaskResponse(
        id=subtask.id,
        task_id=subtask.task_id,
        title=subtask.title,
        completed=subtask.completed,
    )


@app.delete(
    "/tasks/{task_id}/subtasks/{subtask_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_subtask(
    task_id: int,
    subtask_id: int,
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    if not SubtaskRepository(service.repository.db_path).delete_for_user(
        subtask_id, task_id, user.id
    ):
        raise HTTPException(status_code=404, detail="Subtask not found")


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    if not service.repository.delete_for_user(task_id, user.id):
        raise HTTPException(status_code=404, detail="Task not found")
