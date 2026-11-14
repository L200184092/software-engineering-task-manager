from dataclasses import dataclass


@dataclass
class Task:
    """Representasi satu tugas dalam aplikasi."""

    title: str
    description: str = ""
    id: int | None = None
    completed: bool = False
    priority: str = "Medium"
    due_date: str | None = None
    category_id: int | None = None
    recurrence: str = "none"
    next_occurrence_created: bool = False


@dataclass
class User:
    """Representasi satu pengguna aplikasi."""

    username: str
    email: str
    password_hash: str
    id: int | None = None


@dataclass
class Category:
    """Representasi satu kategori tugas."""

    name: str
    user_id: int
    id: int | None = None


@dataclass
class Subtask:
    """Representasi satu subtask yang dimiliki oleh sebuah task."""

    task_id: int
    user_id: int
    title: str
    id: int | None = None
    completed: bool = False


@dataclass
class TaskComment:
    """Komentar milik pengguna pada sebuah task."""

    task_id: int
    user_id: int
    content: str
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class TaskActivity:
    """Catatan aktivitas pada sebuah task."""

    task_id: int
    user_id: int
    action: str
    details: str = ""
    id: int | None = None
    created_at: str | None = None
