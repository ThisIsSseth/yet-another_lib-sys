from dataclasses import dataclass

@dataclass
class Book:
    book_id: int
    title: str
    author: str
    pages: int
    publication_year: int
    copies: int = 1

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Book title cannot be empty.")
        if self.pages < 1:
            raise ValueError("Pages must be positive.")
        if self.copies < 0:
            raise ValueError("Copies cannot be negative.")

    def take_copy(self) -> bool:
        """Remove one available copy. Return False if none are available."""
        if self.copies <= 0:
            return False
        self.copies -= 1
        return True

    def add_copy(self) -> None:
        self.copies += 1

    def __str__(self) -> str:
        return (
            f"[ID={self.book_id}] {self.title} | {self.author} | "
            f"Year: {self.publication_year} | Pages: {self.pages} | "
            f"Copies: {self.copies}"
        )
