from datetime import date
import csv
from pathlib import Path

from .models import Task


CSV_FIELDS = [
    "title",
    "description",
    "completed",
    "priority",
    "due_date",
]


def export_tasks(
    tasks: list[Task],
    file_path: str | Path,
) -> int:
    """Mengekspor daftar tugas ke file CSV."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=CSV_FIELDS,
        )
        writer.writeheader()

        for task in tasks:
            writer.writerow(
                {
                    "title": task.title,
                    "description": task.description,
                    "completed": str(task.completed).lower(),
                    "priority": task.priority,
                    "due_date": task.due_date or "",
                }
            )

    return len(tasks)


def read_tasks(
    file_path: str | Path,
) -> list[Task]:
    """Membaca tugas dari CSV dan memvalidasi format dasarnya."""
    path = Path(file_path)

    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        if reader.fieldnames is None:
            raise ValueError("File CSV kosong atau tidak memiliki header.")

        if (
            len(reader.fieldnames) != len(set(reader.fieldnames))
            or set(reader.fieldnames) != set(CSV_FIELDS)
        ):
            raise ValueError(
                "Header CSV harus berisi kolom: "
                + ", ".join(CSV_FIELDS)
            )

        tasks = []

        for row_number, row in enumerate(reader, start=2):
            title = (row.get("title") or "").strip()
            description = (row.get("description") or "").strip()
            completed_text = (row.get("completed") or "").strip().lower()
            priority = (row.get("priority") or "").strip()
            due_date = (row.get("due_date") or "").strip() or None

            if due_date is not None:
                try:
                    parsed_date = date.fromisoformat(due_date)
                except ValueError as exc:
                    raise ValueError(
                        f"Tanggal tenggat pada baris {row_number} tidak valid."
                    ) from exc

                if parsed_date.isoformat() != due_date:
                    raise ValueError(
                        f"Tanggal tenggat pada baris {row_number} "
                        "harus menggunakan format YYYY-MM-DD."
                    )
            
            if not title:
                raise ValueError(
                    f"Judul tugas pada baris {row_number} tidak boleh kosong."
                )

            if completed_text not in {"true", "false"}:
                raise ValueError(
                    f"Status pada baris {row_number} harus true atau false."
                )

            if priority not in {"Low", "Medium", "High"}:
                raise ValueError(
                    f"Prioritas pada baris {row_number} tidak valid."
                )

            tasks.append(
                Task(
                    title=title,
                    description=description,
                    completed=completed_text == "true",
                    priority=priority,
                    due_date=due_date,
                )
            )

    return tasks
