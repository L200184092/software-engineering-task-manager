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
- Validate task titles, priorities, and due dates.
- Store task data in an SQLite database.
- Automatically initialize the database and migrate existing tables when necessary.
- Run automated tests with pytest.
- Run tests automatically through GitHub Actions on pushes and pull requests to the `main` branch.

## Tech Stack

- **Language:** Python 3.11+
- **Database:** SQLite
- **Testing:** pytest
- **Interface:** Command-line interface (CLI)
- **Continuous Integration:** GitHub Actions

## Project Structure

```text
software-engineering-task-manager/
├── .github/
│   └── workflows/
│       └── python-tests.yml
├── src/
│   └── task_manager/
│       ├── __init__.py
│       ├── cli.py
│       ├── database.py
│       ├── models.py
│       ├── repository.py
│       └── services.py
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   └── test_services.py
├── data/
├── .gitignore
├── README.md
└── requirements.txt
```

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
| 0 | Exit the application |

When creating a task, you can specify its priority and an optional due date. Leave the due date empty if the task has no deadline.

Valid priorities are `Low`, `Medium`, and `High`. Due dates must use the `YYYY-MM-DD` format, for example `2026-10-20`.

## Running Tests

Run the complete test suite with:

```bash
python -m pytest -v
```

The test suite covers task creation, input validation, updates, preservation of existing priority and due dates, due-date removal, task completion, deletion, and CLI interactions.

## Continuous Integration

GitHub Actions automatically runs the test suite when changes are pushed to the `main` branch or when a pull request targets `main`.

The workflow configuration is located at `.github/workflows/python-tests.yml`.

## Architecture

The application separates responsibilities into modules:

- **Models:** Represents task data.
- **Database:** Manages SQLite connections, table initialization, and schema migration.
- **Repository:** Handles database CRUD operations.
- **Services:** Implements business logic and input validation.
- **CLI:** Provides the user interface.
- **Tests:** Verifies application behavior automatically.

## Learning Objectives

This project is part of a practical software engineering portfolio. It demonstrates Python programming, relational database operations, layered architecture, separation of concerns, input validation, automated testing, database schema migration, and continuous integration.

## License

This project is available for educational and portfolio purposes.