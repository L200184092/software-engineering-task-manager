from .database import init_db
from .services import TaskService


def display_tasks(service: TaskService) -> None:
    """Menampilkan seluruh tugas."""
    tasks = service.list_tasks()

    if not tasks:
        print("\nBelum ada tugas.")
        return

    print("\n=== DAFTAR TUGAS ===")
    for task in tasks:
        status = "Selesai" if task.completed else "Belum selesai"
        due_date = task.due_date or "Tidak ada"
        print(f"\n[{task.id}] {task.title} - {status}")
        print(f"    Prioritas: {task.priority}")
        print(f"    Tenggat: {due_date}")

        if task.description:
            print(f"    Deskripsi: {task.description}")


def display_task_results(tasks) -> None:
    """Menampilkan daftar tugas hasil pencarian atau filter."""
    if not tasks:
        print("\nTidak ada tugas yang cocok.")
        return

    print("\n=== HASIL TUGAS ===")
    for task in tasks:
        status = "Selesai" if task.completed else "Belum selesai"
        due_date = task.due_date or "Tidak ada"
        print(
            f"[{task.id}] {task.title} - {status} "
            f"| Prioritas: {task.priority} "
            f"| Tenggat: {due_date}"
        )
        if task.description:
            print(f"    Deskripsi: {task.description}")

def ask_priority(current_priority: str = "Medium") -> str:
    """Meminta prioritas tugas dari pengguna."""
    print("Pilihan prioritas: Low, Medium, High")
    priority = input(
        f"Prioritas [{current_priority}]: "
    ).strip()

    return priority or current_priority


def ask_due_date(current_due_date: str | None = None) -> str | None:
    """Meminta tenggat tugas; input kosong mempertahankan nilai saat ini."""
    current_value = current_due_date or "Tidak ada"
    due_date = input(
        f"Tenggat YYYY-MM-DD [{current_value}] "
        "(kosongkan untuk mempertahankan): "
    ).strip()

    if not due_date:
        return current_due_date

    return due_date


def main() -> None:
    init_db()
    service = TaskService()

    while True:
        print("\n=== SOFTWARE ENGINEERING TASK MANAGER ===")
        print("1. Tambah tugas")
        print("2. Lihat semua tugas")
        print("3. Perbarui tugas")
        print("4. Tandai tugas selesai")
        print("5. Hapus tugas")
        print("6. Cari tugas")
        print("7. Filter tugas")
        print("8. Urutkan tugas")
        print("0. Keluar")

        choice = input("Pilih menu: ").strip()

        if choice == "1":
            title = input("Judul tugas: ")
            description = input("Deskripsi tugas (opsional): ")
            priority = ask_priority()
            due_date = input(
                "Tenggat YYYY-MM-DD (kosongkan jika tidak ada): "
            ).strip() or None

            try:
                task = service.create_task(
                    title,
                    description,
                    priority,
                    due_date,
                )
                print(f"Tugas berhasil ditambahkan dengan ID {task.id}.")
            except ValueError as error:
                print(f"Gagal menambahkan tugas: {error}")

        elif choice == "2":
            display_tasks(service)

        elif choice == "3":
            try:
                task_id = int(input("ID tugas yang akan diperbarui: "))
                existing_task = next(
                    (
                        task
                        for task in service.list_tasks()
                        if task.id == task_id
                    ),
                    None,
                )

                if existing_task is None:
                    print("Tugas tidak ditemukan.")
                    continue

                title = input(
                    f"Judul baru [{existing_task.title}]: "
                ).strip() or existing_task.title
                description = input(
                    f"Deskripsi baru [{existing_task.description}]: "
                ).strip() or existing_task.description
                priority = ask_priority(existing_task.priority)
                due_date = ask_due_date(existing_task.due_date)

                if service.update_task(
                    task_id,
                    title,
                    description,
                    priority,
                    due_date,
                ):
                    print("Tugas berhasil diperbarui.")
                else:
                    print("Tugas tidak ditemukan.")

            except ValueError as error:
                print(f"Gagal memperbarui tugas: {error}")

        elif choice == "4":
            try:
                task_id = int(input("ID tugas yang selesai: "))

                if service.complete_task(task_id):
                    print("Tugas berhasil ditandai selesai.")
                else:
                    print("Tugas tidak ditemukan.")
            except ValueError:
                print("ID harus berupa angka.")

        elif choice == "5":
            try:
                task_id = int(input("ID tugas yang akan dihapus: "))

                if service.delete_task(task_id):
                    print("Tugas berhasil dihapus.")
                else:
                    print("Tugas tidak ditemukan.")
            except ValueError:
                print("ID harus berupa angka.")


        elif choice == "6":
            query = input("Masukkan kata kunci: ")
            results = service.search_tasks(query)
            display_task_results(results)

        elif choice == "7":
            print("Filter berdasarkan:")
            print("1. Belum selesai")
            print("2. Selesai")
            print("3. Prioritas")
            print("4. Belum selesai dengan prioritas High")

            filter_choice = input("Pilih filter: ").strip()

            if filter_choice == "1":
                results = service.filter_tasks(completed=False)
            elif filter_choice == "2":
                results = service.filter_tasks(completed=True)
            elif filter_choice == "3":
                priority = input(
                    "Prioritas (Low, Medium, High): "
                ).strip()
                try:
                    results = service.filter_tasks(priority=priority)
                except ValueError as error:
                    print(f"Filter gagal: {error}")
                    continue
            elif filter_choice == "4":
                results = service.filter_tasks(
                    completed=False,
                    priority="High",
                )
            else:
                print("Pilihan filter tidak valid.")
                continue

            display_task_results(results)

        elif choice == "8":
            print("\n=== URUTKAN TUGAS ===")
            print("1. Berdasarkan prioritas (High ke Low)")
            print("2. Berdasarkan tenggat (terdekat)")

            sort_choice = input("Pilih pengurutan: ").strip()

            if sort_choice == "1":
                results = service.sort_tasks("priority")
                display_task_results(results)
            elif sort_choice == "2":
                results = service.sort_tasks("due_date")
                display_task_results(results)
            else:
                print("Pilihan pengurutan tidak valid.")

        elif choice == "0":
            print("Terima kasih telah menggunakan aplikasi.")
            break

        else:
            print("Pilihan tidak valid. Silakan pilih menu yang tersedia.")


if __name__ == "__main__":
    main()