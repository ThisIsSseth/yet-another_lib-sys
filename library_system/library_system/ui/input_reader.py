class InputReader:
    def read_int(self, prompt: str, minimum: int, maximum: int) -> int:
        while True:
            raw = input(prompt).strip()
            try:
                value = int(raw)
            except ValueError:
                print("Enter a whole number.")
                continue
            if minimum <= value <= maximum:
                return value
            print(f"Enter a number from {minimum} to {maximum}.")

    def read_text(self, prompt: str) -> str:
        while True:
            value = input(prompt).strip()
            if value:
                return value
            print("This field cannot be empty.")
