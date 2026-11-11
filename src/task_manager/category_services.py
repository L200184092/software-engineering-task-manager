
import sqlite3

from .category_repository import CategoryRepository
from .models import Category


class CategoryService:
    """Menangani validasi dan aturan bisnis kategori tugas."""

    def __init__(self, repository: CategoryRepository):
        self.repository = repository

    def create_category(self, name: str, user_id: int) -> Category:
        """Membuat kategori baru setelah validasi."""
        name = self._validate_name(name)

        category = Category(name=name, user_id=user_id)

        try:
            return self.repository.create_for_user(category)
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Nama kategori sudah digunakan."
            ) from exc

    def get_categories(self, user_id: int) -> list[Category]:
        """Mengambil seluruh kategori milik pengguna."""
        return self.repository.get_all_for_user(user_id)

    def get_category(
        self,
        category_id: int,
        user_id: int,
    ) -> Category | None:
        """Mengambil kategori berdasarkan ID dan pemiliknya."""
        return self.repository.get_for_user(category_id, user_id)

    def update_category(
        self,
        category_id: int,
        user_id: int,
        name: str,
    ) -> Category:
        """Memperbarui kategori milik pengguna."""
        name = self._validate_name(name)

        existing = self.repository.get_for_user(category_id, user_id)
        if existing is None:
            raise ValueError("Kategori tidak ditemukan.")

        try:
            self.repository.update_for_user(
                category_id,
                user_id,
                name,
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Nama kategori sudah digunakan."
            ) from exc

        existing.name = name
        return existing

    def delete_category(self, category_id: int, user_id: int) -> bool:
        """Menghapus kategori milik pengguna."""
        deleted = self.repository.delete_for_user(category_id, user_id)

        if not deleted:
            raise ValueError("Kategori tidak ditemukan.")

        return True

    @staticmethod
    def _validate_name(name: str) -> str:
        """Memastikan nama kategori tidak kosong."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Nama kategori tidak boleh kosong.")

        return name.strip()
