# Software Engineering Task Manager

A task management application built with Python, SQLite, and FastAPI. It demonstrates software engineering practices including layered architecture, CRUD operations, input validation, persistent storage, automated testing, and continuous integration with GitHub Actions.

## Features

- Create new tasks with a title and optional description.
- Assign task priorities: `Low`, `Medium`, or `High`.
- Set an optional due date using the `YYYY-MM-DD` format.
- View all tasks, including their status, priority, due date, and description.
- Update task information while preserving optional values that are not provided.
- Mark tasks as completed.
- Delete tasks.
- Access task management functionality through a FastAPI REST API.
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
- Back up and restore the SQLite database using the SQLite Backup API.
- Validate database integrity and schema before restoring a backup.
- Require explicit confirmation before restoring a database to prevent accidental data replacement.



## Tech Stack

- **Language:** Python 3.11+
- **Database:** SQLite
- **API Framework:** FastAPI
- **API Server:** Uvicorn
- **Testing:** pytest and FastAPI TestClient
- **Interfaces:** Command-line interface (CLI) and REST API
- **Continuous Integration:** GitHub Actions

## Project Structure

software-engineering-task-manager/
├── .github/
│   └── workflows/
│       └── python-tests.yml
├── src/
│   └── task_manager/
│       ├── __init__.py
│       ├── api.py
│       ├── cli.py
│       ├── backup.py
│       ├── csv_handler.py
│       ├── database.py
│       ├── models.py
│       ├── repository.py
│       └── services.py
├── tests/
│   ├── __init__.py
│   ├── test_api.py
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

The current test suite contains 61 tests.

## Continuous Integration

GitHub Actions automatically runs the test suite when changes are pushed to the `main` branch or when a pull request targets `main`.

The workflow configuration is located at `.github/workflows/python-tests.yml`.

## Architecture

The application separates responsibilities into modules:

- **Models:** Represents task data.
- **Database:** Manages SQLite connections, table initialization, and schema migration.
- **Repository:** Handles database CRUD operations.
- **Services:** Implements business logic, searching, filtering, sorting, and input validation.
- **CLI:** Provides the command-line user interface.
- **REST API:** Exposes task management operations through FastAPI.
- **Tests:** Verify application behavior automatically, including API endpoints.
- **CSV Handler:** Reads, validates, and writes task data in CSV format.
- **Backup:** Creates and restores SQLite database backups with validation.

## Learning Objectives

This project is part of a practical software engineering portfolio. It demonstrates Python programming, relational database operations, layered architecture, separation of concerns, input validation, searching, filtering, sorting, automated testing, database schema migration, and continuous integration.

## License

This project is available for educational and portfolio purposes.

## Database Backup and Restore

### Creating a Backup

1. Run the application using `python -m src.task_manager.cli`.
2. Select menu option `12` to back up the database.
3. Enter a backup file path, or press Enter to use the default path: `data/tasks_backup.db`.

### Restoring a Database

1. Ensure the database is not being used by another process.
2. Run the application and select menu option `13` to restore the database.
3. Enter the path of the backup file to restore.
4. Type `RESTORE` to confirm the operation.

**Warning:** Restoring replaces the active database contents with the contents of the backup file. Verify the backup file and create a recent backup before restoring.

## REST API

The project provides a REST API built with FastAPI for managing tasks.

### Running the API

Activate the virtual environment, then run the following commands from the project root directory:

```powershell
$env:PYTHONPATH = "src"
python -m uvicorn task_manager.api:app --reload
```

### API Documentation

Once the server is running, open:

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

### Endpoint

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Check API status |
| GET | `/tasks` | Retrieve all tasks |
| POST | `/tasks` | Create a task |
| GET | `/tasks/{task_id}` | Retrieve a task by ID |
| PUT | `/tasks/{task_id}` | Update a task |
| PATCH | `/tasks/{task_id}/complete` | Mark a task as completed |
| DELETE | `/tasks/{task_id}` | Delete a task |

### Running Tests

Run the complete test suite with:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -v
```
