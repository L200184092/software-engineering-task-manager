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
        print(f"[{task.id}] {task.title} - {status}")
        if task.description:
            print(f"    Deskripsi: {task.description}")


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
        print("0. Keluar")

        choice = input("Pilih menu: ").strip()

        if choice == "1":
            title = input("Judul tugas: ")
            description = input("Deskripsi tugas (opsional): ")

            try:
                task = service.create_task(title, description)
                print(f"Tugas berhasil ditambahkan dengan ID {task.id}.")
            except ValueError as error:
                print(f"Gagal menambahkan tugas: {error}")

        elif choice == "2":
            display_tasks(service)

        elif choice == "3":
            try:
                task_id = int(input("ID tugas yang akan diperbarui: "))
                title = input("Judul baru: ")
                description = input("Deskripsi baru: ")

                if service.update_task(task_id, title, description):
                    print("Tugas berhasil diperbarui.")
                else:
                    print("Tugas tidak ditemukan.")
            except ValueError:
                print("ID harus berupa angka dan judul tidak boleh kosong.")

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

        elif choice == "0":
            print("Terima kasih telah menggunakan aplikasi.")
            break

        else:
            print("Pilihan tidak valid. Silakan pilih menu yang tersedia.")


if __name__ == "__main__":
    main()
