from datetime import date
from .models import Task
from .repository import TaskRepository

_UNSET = object()

class TaskService:
    """Menangani logika bisnis dan validasi tugas."""

    VALID_PRIORITIES = {"Low", "Medium", "High"}

    def __init__(self, repository: TaskRepository | None = None) -> None:
        self.repository = repository or TaskRepository()

    @staticmethod
    def _validate_due_date(due_date: str | None) -> str | None:
        """Memvalidasi tenggat waktu dengan format YYYY-MM-DD."""
        if due_date is None or not due_date.strip():
            return None

        due_date = due_date.strip()

        try:
            parsed_date = date.fromisoformat(due_date)
        except ValueError as exc:
            raise ValueError(
                "Tanggal tenggat harus valid dengan format YYYY-MM-DD."
            ) from exc

        if parsed_date.isoformat() != due_date:
            raise ValueError(
                "Tanggal tenggat harus menggunakan format YYYY-MM-DD."
            )

        return due_date

    @classmethod
    def _validate_priority(cls, priority: str) -> str:
        """Memastikan prioritas termasuk Low, Medium, atau High."""
        if priority not in cls.VALID_PRIORITIES:
            raise ValueError(
                "Prioritas harus Low, Medium, atau High."
            )

        return priority

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "Medium",
        due_date: str | None = None,
    ) -> Task:
        """Membuat tugas baru setelah memvalidasi input."""
        title = title.strip()
        description = description.strip()
        priority = self._validate_priority(priority)
        due_date = self._validate_due_date(due_date)

        if not title:
            raise ValueError("Judul tugas tidak boleh kosong.")

        return self.repository.create(
            Task(
                title=title,
                description=description,
                priority=priority,
                due_date=due_date,
            )
        )

    def list_tasks(self) -> list[Task]:
        """Mengambil seluruh tugas."""
        return self.repository.get_all()

    def search_tasks(self, query: str) -> list[Task]:
        """Mencari tugas berdasarkan judul atau deskripsi."""
        query = query.strip().casefold()

        if not query:
            return self.list_tasks()

        return [
            task
            for task in self.list_tasks()
            if query in task.title.casefold()
            or query in task.description.casefold()
        ]

    def filter_tasks(
        self,
        completed: bool | None = None,
        priority: str | None = None,
    ) -> list[Task]:
        """Memfilter tugas berdasarkan status dan prioritas."""
        tasks = self.list_tasks()

        if completed is not None:
            tasks = [
                task for task in tasks
                if task.completed == completed
            ]

        if priority is not None:
            priority = self._validate_priority(priority)
            tasks = [
                task for task in tasks
                if task.priority == priority
            ]

        return tasks

    def sort_tasks(
        self,
        sort_by: str = "priority",
    ) -> list[Task]:
        """Mengurutkan tugas berdasarkan prioritas atau tenggat."""
        tasks = self.list_tasks()

        if sort_by == "priority":
            priority_order = {
                "High": 0,
                "Medium": 1,
                "Low": 2,
            }
            return sorted(
                tasks,
                key=lambda task: priority_order[task.priority],
            )

        if sort_by == "due_date":
            return sorted(
                tasks,
                key=lambda task: (
                    task.due_date is None,
                    task.due_date or "",
                ),
            )

        raise ValueError(
            "Pengurutan harus menggunakan 'priority' atau 'due_date'."
        )

    def update_task(
        self,
        task_id: int,
        title: str,
        description: str = "",
        priority: str | None = None,
        due_date: str | None | object = _UNSET,
    ) -> bool:
        """Memperbarui tugas tanpa mengubah nilai opsional yang tidak diberikan."""
        title = title.strip()
        description = description.strip()

        if not title:
            raise ValueError("Judul tugas tidak boleh kosong.")

        task = next(
            (
                item
                for item in self.repository.get_all()
                if item.id == task_id
            ),
            None,
        )

        if task is None:
            return False

        if priority is not None:
            task.priority = self._validate_priority(priority)

        if due_date is not _UNSET:
            task.due_date = self._validate_due_date(due_date)

        task.title = title
        task.description = description

        return self.repository.update(task)

    def complete_task(self, task_id: int) -> bool:
        """Menandai tugas sebagai selesai."""
        task = next(
            (
                item
                for item in self.repository.get_all()
                if item.id == task_id
            ),
            None,
        )

        if task is None:
            return False

        task.completed = True
        return self.repository.update(task)

    def delete_task(self, task_id: int) -> bool:
        """Menghapus tugas berdasarkan ID."""
        return self.repository.delete(task_id)

    def get_task_statistics(self) -> dict:
        """Menghitung statistik tugas."""
        tasks = self.list_tasks()

        total = len(tasks)
        completed = sum(1 for task in tasks if task.completed)
        pending = total - completed

        priority_counts = {
            "High": sum(1 for task in tasks if task.priority == "High"),
            "Medium": sum(1 for task in tasks if task.priority == "Medium"),
            "Low": sum(1 for task in tasks if task.priority == "Low"),
        }

        completion_rate = (
            round((completed / total) * 100, 2)
            if total > 0
            else 0.0
        )

        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "completion_rate": completion_rate,
            "priority_counts": priority_counts,
        }
