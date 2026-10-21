
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from .repository import TaskRepository
from .services import TaskService


app = FastAPI(
    title="Software Engineering Task Manager API",
    description="REST API untuk mengelola tugas menggunakan SQLite.",
    version="1.0.0",
)


def get_task_service() -> TaskService:
    """Menyediakan service untuk endpoint API."""
    return TaskService(repository=TaskRepository())


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


def find_task(task_id: int, service: TaskService):
    """Mencari tugas berdasarkan ID."""
    return next(
        (task for task in service.list_tasks() if task.id == task_id),
        None,
    )


@app.get("/")
def root():
    return {
        "message": "Task Manager API is running",
        "docs": "/docs",
    }


@app.get("/tasks", response_model=list[TaskResponse])
def list_tasks(service: TaskService = Depends(get_task_service)):
    return service.list_tasks()


@app.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    payload: TaskCreate,
    service: TaskService = Depends(get_task_service),
):
    try:
        return service.create_task(
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            due_date=payload.due_date,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    service: TaskService = Depends(get_task_service),
):
    task = find_task(task_id, service)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    service: TaskService = Depends(get_task_service),
):
    try:
        updated = service.update_task(
            task_id=task_id,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            due_date=payload.due_date,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return find_task(task_id, service)


@app.patch("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: int,
    service: TaskService = Depends(get_task_service),
):
    completed = service.complete_task(task_id)

    if not completed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return find_task(task_id, service)


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    service: TaskService = Depends(get_task_service),
):
    deleted = service.delete_task(task_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return None
