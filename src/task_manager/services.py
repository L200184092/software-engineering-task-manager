
from .models import Task
from .repository import TaskRepository


class TaskService:
    """Menangani logika bisnis dan validasi tugas."""

    def __init__(self, repository: TaskRepository | None = None) -> None:
        self.repository = repository or TaskRepository()

    def create_task(self, title: str, description: str = "") -> Task:
        """Membuat tugas baru setelah memvalidasi input."""
        title = title.strip()
        description = description.strip()

        if not title:
            raise ValueError("Judul tugas tidak boleh kosong.")

        return self.repository.create(
            Task(title=title, description=description)
        )

    def list_tasks(self) -> list[Task]:
        """Mengambil seluruh tugas."""
        return self.repository.get_all()

    def update_task(
        self,
        task_id: int,
        title: str,
        description: str = "",
    ) -> bool:
        """Memperbarui judul dan deskripsi tugas."""
        title = title.strip()
        description = description.strip()

        if not title:
            raise ValueError("Judul tugas tidak boleh kosong.")

        task = next(
            (item for item in self.repository.get_all()
             if item.id == task_id),
            None,
        )

        if task is None:
            return False

        task.title = title
        task.description = description
        return self.repository.update(task)

    def complete_task(self, task_id: int) -> bool:
        """Menandai tugas sebagai selesai."""
        task = next(
            (item for item in self.repository.get_all()
             if item.id == task_id),
            None,
        )

        if task is None:
            return False

        task.completed = True
        return self.repository.update(task)

    def delete_task(self, task_id: int) -> bool:
        """Menghapus tugas berdasarkan ID."""
        return self.repository.delete(task_id)
