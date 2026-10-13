# Software Engineering Task Manager

A simple command-line task management application built with Python and SQLite. This project demonstrates fundamental software engineering practices, including layered architecture, CRUD operations, input validation, and automated testing with pytest.

## Features

- Create a new task.
- View all tasks.
- Update task titles and descriptions.
- Mark tasks as completed.
- Delete tasks.
- Validate task titles.
- Store task data in an SQLite database.
- Run automated tests with pytest.

## Tech Stack

- **Language:** Python 3.11+
- **Database:** SQLite
- **Testing:** pytest
- **Interface:** Command-line interface (CLI)

## Project Structure

```text
software-engineering-task-manager/
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

The SQLite database is created automatically when tasks are accessed, provided the database directory is available.

## Running Tests

Run the test suite with:

```bash
python -m pytest -v
```

The tests cover task creation, validation, updating, completion, deletion, and CLI interactions.

## Architecture

The application separates responsibilities into modules:

- **Models:** Represents task data.
- **Database:** Manages SQLite connections and table initialization.
- **Repository:** Handles database CRUD operations.
- **Services:** Implements business logic and validation.
- **CLI:** Provides the user interface.
- **Tests:** Verifies application behavior automatically.

## Learning Objectives

This project is part of a practical software engineering portfolio and demonstrates Python programming, relational database operations, separation of concerns, input validation, and automated testing.

## License

This project is available for educational and portfolio purposes.
