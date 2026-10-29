
import sqlite3
import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from .auth import create_access_token, decode_access_token, hash_password, verify_password
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


class TaskUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    priority: str | None = None
    due_date: str | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    completed: bool
    priority: str
    due_date: str | None


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
            "SELECT id, username, email, password_hash FROM users WHERE id=?", (user_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return User(id=row["id"], username=row["username"], email=row["email"],
                password_hash=row["password_hash"])


@app.get("/")
def root():
    return {"message": "Task Manager API is running", "docs": "/docs"}


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, users: UserRepository = Depends(get_user_repository)):
    user = User(username=payload.username.strip(), email=str(payload.email).lower(),
                password_hash=hash_password(payload.password))
    try:
        created = users.create(user)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Username or email already registered") from exc
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

    return TokenResponse(
        access_token=create_access_token(str(user.id))
    )


@app.get("/tasks", response_model=list[TaskResponse])
def list_tasks(user: User = Depends(get_current_user),
               service: TaskService = Depends(get_task_service)):
    return service.repository.get_all_for_user(user.id)


@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, user: User = Depends(get_current_user),
                service: TaskService = Depends(get_task_service)):
    try:
        title = payload.title.strip()
        description = payload.description.strip()
        if not title:
            raise ValueError("Judul tugas tidak boleh kosong.")
        priority = service._validate_priority(payload.priority)
        due_date = service._validate_due_date(payload.due_date)
        return service.repository.create_for_user(
            Task(title=title, description=description, priority=priority, due_date=due_date),
            user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, user: User = Depends(get_current_user),
             service: TaskService = Depends(get_task_service)):
    task = service.repository.get_for_user(task_id, user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, payload: TaskUpdate, user: User = Depends(get_current_user),
                service: TaskService = Depends(get_task_service)):
    try:
        title = payload.title.strip()
        description = payload.description.strip()
        if not title:
            raise ValueError("Judul tugas tidak boleh kosong.")
        priority = service._validate_priority(payload.priority or "Medium")
        due_date = service._validate_due_date(payload.due_date)
        updated = service.repository.update_for_user(
            task_id, user.id, title=title, description=description,
            priority=priority, due_date=due_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return service.repository.get_for_user(task_id, user.id)


@app.patch("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: int, user: User = Depends(get_current_user),
                  service: TaskService = Depends(get_task_service)):
    if not service.repository.complete_for_user(task_id, user.id):
        raise HTTPException(status_code=404, detail="Task not found")
    return service.repository.get_for_user(task_id, user.id)


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, user: User = Depends(get_current_user),
                service: TaskService = Depends(get_task_service)):
    if not service.repository.delete_for_user(task_id, user.id):
        raise HTTPException(status_code=404, detail="Task not found")
    return None
