# Software Engineering Task Manager

A command-line task management application built with Python and SQLite. This project demonstrates software engineering practices such as layered architecture, CRUD operations, input validation, database persistence, automated testing, and continuous integration with GitHub Actions.

## Features

- Create new tasks with a title and optional description.
- Assign task priorities: `Low`, `Medium`, or `High`.
- Set an optional due date using the `YYYY-MM-DD` format.
- View all tasks, including their status, priority, due date, and description.
- Update task information while preserving optional values that are not provided.
- Mark tasks as completed.
- Delete tasks.
- Store task data in an SQLite database.
- Automatically initialize the database and migrate existing tables when necessary.
- Run automated tests with pytest.
- Run tests automatically through GitHub Actions on pushes and pull requests to the `main` branch.
- Search tasks by title or description using case-insensitive matching.
- Filter tasks by completion status and priority.
- Sort tasks by priority and due date.
- View task statistics, including total, completed, and pending tasks, completion rate, and priority distribution.
- Export tasks to CSV files.
- Import tasks from CSV files with data validation before saving.
- Database backup dan restore menggunakan SQLite Backup API.
- Validasi integritas dan skema database sebelum restore.
- Konfirmasi eksplisit sebelum restore untuk mencegah pemulihan yang tidak disengaja.



## Tech Stack

- **Language:** Python 3.11+
- **Database:** SQLite
- **Testing:** pytest
- **Interface:** Command-line interface (CLI)
- **Continuous Integration:** GitHub Actions

## Project Structure

software-engineering-task-manager/
├── .github/
│   └── workflows/
│       └── python-tests.yml
├── src/
│   └── task_manager/
│       ├── __init__.py
│       ├── cli.py
│       ├── backup.py
│       ├── csv_handler.py
│       ├── database.py
│       ├── models.py
│       ├── repository.py
│       └── services.py
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_csv_handler.py
│   ├── test_services.py
│   └── test_backup.py
├── data/
├── .gitignore
├── README.md
└── requirements.txt

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/L200184092/software-engineering-task-manager.git
cd software-engineering-task-manager
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Run the application

```bash
python -m src.task_manager.cli
```

Follow the on-screen menu to manage tasks.

The SQLite database is initialized automatically when the application starts.

## Using the Application

The application provides the following menu options:

| Option | Action |
|---|---|
| 1 | Add a task |
| 2 | View all tasks |
| 3 | Update a task |
| 4 | Mark a task as completed |
| 5 | Delete a task |
| 6 | Search tasks |
| 7 | Filter tasks |
| 8 | Sort tasks |
| 9 | View task statistics |
| 10 | Export tasks to CSV |
| 11 | Import tasks from CSV |
| 12 | Back up the database |
| 13 | Restore the database |
| 0 | Exit the application |

### CSV Import and Export

Use menu option `10` to export all tasks to a CSV file. The default output path is `data/tasks_export.csv`. You can also enter a custom file path.

Use menu option `11` to import tasks from a CSV file.

The CSV file must contain these columns:

- `title`
- `description`
- `completed`
- `priority`
- `due_date`

The `completed` column accepts `true` or `false`. The `priority` column accepts `Low`, `Medium`, or `High`. Due dates must use the `YYYY-MM-DD` format or be left empty.

Imported tasks are added as new records; they do not update existing tasks. The application validates the CSV data before saving imported tasks.


### Task priorities and due dates

When creating a task, you can specify its priority and an optional due date. Leave the due date empty if the task has no deadline.

Valid priorities are `Low`, `Medium`, and `High`. Due dates must use the `YYYY-MM-DD` format, for example `2026-10-20`.

### Search tasks

Use menu option `6` to search for tasks by title or description. The search is case-insensitive.

### Filter tasks

Use menu option `7` to filter tasks by:

- Incomplete tasks.
- Completed tasks.
- Priority.
- Incomplete tasks with `High` priority.

### Sort tasks

Use menu option `8` to sort tasks by:

- **Priority:** `High`, then `Medium`, then `Low`.
- **Due date:** Earliest date first. Tasks without due dates appear last.

## Running Tests

Run the complete test suite with:

```bash
python -m pytest -v
```

The test suite covers task creation, input validation, updates, task completion, deletion, search, filtering, sorting, task statistics, CSV import and export, and CLI interactions.

The current test suite contains 55 tests.

## Continuous Integration

GitHub Actions automatically runs the test suite when changes are pushed to the `main` branch or when a pull request targets `main`.

The workflow configuration is located at `.github/workflows/python-tests.yml`.

## Architecture

The application separates responsibilities into modules:

- **Models:** Represents task data.
- **Database:** Manages SQLite connections, table initialization, and schema migration.
- **Repository:** Handles database CRUD operations.
- **Services:** Implements business logic, searching, filtering, sorting, and input validation.
- **CLI:** Provides the user interface.
- **Tests:** Verifies application behavior automatically.
- **CSV Handler:** Reads, validates, and writes task data in CSV format.

## Learning Objectives

This project is part of a practical software engineering portfolio. It demonstrates Python programming, relational database operations, layered architecture, separation of concerns, input validation, searching, filtering, sorting, automated testing, database schema migration, and continuous integration.

## License

This project is available for educational and portfolio purposes.

## Backup dan Restore Database

### Membuat Backup

1. Jalankan aplikasi:
   `python -m src.task_manager.cli`
2. Pilih menu `12. Backup database`.
3. Masukkan lokasi file backup atau tekan Enter untuk menggunakan lokasi default:
   `data/tasks_backup.db`

### Memulihkan Database

1. Pastikan aplikasi tidak sedang digunakan oleh proses lain.
2. Jalankan aplikasi dan pilih menu `13. Restore database`.
3. Masukkan lokasi file backup yang akan dipulihkan.
4. Ketik `RESTORE` untuk mengonfirmasi pemulihan.

**Peringatan:** Restore akan mengganti isi database aktif dengan isi database dari file backup. Pastikan file backup benar dan buat backup terbaru sebelum melakukan restore.

### Menjalankan Pengujian

Jalankan seluruh pengujian dengan perintah:

`python -m pytest -v`
