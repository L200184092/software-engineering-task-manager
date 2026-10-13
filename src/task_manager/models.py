
from dataclasses import dataclass


@dataclass
class Task:
    """Representasi satu tugas dalam aplikasi."""

    title: str
    description: str = ""
    id: int | None = None
    completed: bool = False
