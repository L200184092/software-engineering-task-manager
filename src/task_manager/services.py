from datetime import date
from pathlib import Path
from typing import ClassVar

from .csv_handler import export_tasks, read_tasks
from .models import Task
from .repository import TaskRepository

_UNSET = object()


class TaskService:
    """Menangani logika bisnis dan validasi tugas."""

    VALID_PRIORITIES: ClassVar[set[str]] = {"Low", "Medium", "High"}

    def __init__(self, repository: TaskRepository | None = None) -> None:
        self.repository = repository or TaskRepository()

    @staticmethod
    def validate_due_date(due_date: str | None) -> str | None:
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
            raise ValueError("Tanggal tenggat harus menggunakan format YYYY-MM-DD.")

        return due_date

    @staticmethod
    def get_deadline_status(
        task: Task,
        today: date | None = None,
    ) -> str:
        """Menentukan status deadline sebuah tugas."""
        if task.completed:
            return "Completed"

        if task.due_date is None:
            return "No Deadline"

        today = today or date.today()
        due_date = date.fromisoformat(task.due_date)
        days_remaining = (due_date - today).days

        if days_remaining < 0:
            return "Overdue"

        if days_remaining == 0:
            return "Due Today"

        if days_remaining <= 7:
            return "Upcoming"

        return "Future"

    @classmethod
    def validate_priority(cls, priority: str) -> str:
        """Memastikan prioritas termasuk Low, Medium, atau High."""
        if priority not in cls.VALID_PRIORITIES:
            raise ValueError("Prioritas harus Low, Medium, atau High.")

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
        priority = self.validate_priority(priority)
        due_date = self.validate_due_date(due_date)

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
            if query in task.title.casefold() or query in task.description.casefold()
        ]

    def filter_tasks(
        self,
        completed: bool | None = None,
        priority: str | None = None,
    ) -> list[Task]:
        """Memfilter tugas berdasarkan status dan prioritas."""
        tasks = self.list_tasks()

        if completed is not None:
            tasks = [task for task in tasks if task.completed == completed]

        if priority is not None:
            priority = self.validate_priority(priority)
            tasks = [task for task in tasks if task.priority == priority]

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

        raise ValueError("Pengurutan harus menggunakan 'priority' atau 'due_date'.")

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
            (item for item in self.repository.get_all() if item.id == task_id),
            None,
        )

        if task is None:
            return False

        if priority is not None:
            task.priority = self.validate_priority(priority)

        if due_date is not _UNSET:
            task.due_date = self.validate_due_date(due_date)

        task.title = title
        task.description = description

        return self.repository.update(task)

    def complete_task(self, task_id: int) -> bool:
        """Menandai tugas sebagai selesai."""
        task = next(
            (item for item in self.repository.get_all() if item.id == task_id),
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

        completion_rate = round((completed / total) * 100, 2) if total > 0 else 0.0

        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "completion_rate": completion_rate,
            "priority_counts": priority_counts,
        }

    def get_user_task_statistics(self, user_id: int) -> dict:
        """Menghitung statistik tugas milik pengguna tertentu."""
        tasks = self.repository.get_all_for_user_statistics(user_id)

        total = len(tasks)
        completed = sum(1 for task in tasks if task.completed)
        pending = total - completed

        priority_distribution = {
            "low": sum(1 for task in tasks if task.priority == "Low"),
            "medium": sum(1 for task in tasks if task.priority == "Medium"),
            "high": sum(1 for task in tasks if task.priority == "High"),
        }

        deadline_distribution = {
            "overdue": 0,
            "due_today": 0,
            "upcoming": 0,
            "future": 0,
            "no_deadline": 0,
            "completed": 0,
        }

        status_mapping = {
            "Overdue": "overdue",
            "Due Today": "due_today",
            "Upcoming": "upcoming",
            "Future": "future",
            "No Deadline": "no_deadline",
            "Completed": "completed",
        }

        for task in tasks:
            status = self.get_deadline_status(task)
            deadline_distribution[status_mapping[status]] += 1

        completion_rate = round((completed / total) * 100, 2) if total > 0 else 0.0

        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "pending_tasks": pending,
            "completion_rate": completion_rate,
            "priority_distribution": priority_distribution,
            "deadline_distribution": deadline_distribution,
        }

    def get_user_task_dashboard(self, user_id: int) -> dict:
        """Menyusun ringkasan dashboard tugas milik pengguna."""
        tasks = self.repository.get_all_for_user_statistics(user_id)
        today = date.today()

        total = len(tasks)
        completed = sum(1 for task in tasks if task.completed)
        pending = total - completed

        deadline_overview = {
            "overdue": 0,
            "due_today": 0,
            "upcoming": 0,
            "future": 0,
            "no_deadline": 0,
            "completed": 0,
        }

        status_mapping = {
            "Overdue": "overdue",
            "Due Today": "due_today",
            "Upcoming": "upcoming",
            "Future": "future",
            "No Deadline": "no_deadline",
            "Completed": "completed",
        }

        for task in tasks:
            status = self.get_deadline_status(task, today=today)
            deadline_overview[status_mapping[status]] += 1

        priority_tasks = sorted(
            [task for task in tasks if not task.completed and task.priority == "High"],
            key=lambda task: (
                task.due_date is None,
                task.due_date or "",
                task.id or 0,
            ),
        )[:5]

        upcoming_deadlines = sorted(
            [
                task
                for task in tasks
                if (
                    not task.completed
                    and task.due_date is not None
                    and task.due_date >= today.isoformat()
                )
            ],
            key=lambda task: (task.due_date, task.id or 0),
        )[:5]

        def serialize_task(task: Task) -> dict:
            return {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "priority": task.priority,
                "due_date": task.due_date,
                "deadline_status": self.get_deadline_status(
                    task,
                    today=today,
                ),
            }

        return {
            "summary": {
                "total_tasks": total,
                "completed_tasks": completed,
                "pending_tasks": pending,
                "completion_rate": (
                    round((completed / total) * 100, 2) if total > 0 else 0.0
                ),
            },
            "deadline_overview": deadline_overview,
            "priority_tasks": [serialize_task(task) for task in priority_tasks],
            "upcoming_deadlines": [serialize_task(task) for task in upcoming_deadlines],
        }

    def export_tasks_to_csv(self, file_path: str | Path) -> int:
        """Mengekspor semua tugas ke file CSV."""
        tasks = self.list_tasks()
        return export_tasks(tasks, file_path)

    def import_tasks_from_csv(self, file_path: str | Path) -> int:
        """Mengimpor tugas dari CSV setelah seluruh data valid."""
        tasks = read_tasks(file_path)

        # Validasi seluruh data sebelum menyimpan tugas apa pun.
        for task in tasks:
            task.title = task.title.strip()
            task.description = task.description.strip()
            task.priority = self.validate_priority(task.priority)
            task.due_date = self.validate_due_date(task.due_date)

            if not task.title:
                raise ValueError("Judul tugas tidak boleh kosong.")

        # Simpan hanya setelah seluruh data berhasil divalidasi.
        for task in tasks:
            self.repository.create(task)

        return len(tasks)
