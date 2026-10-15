# Library System — Python port

This is the first working port of the Java `librarysystem2` console project. It keeps the model / service / controller / storage separation and uses JSON persistence.

## Run

From the directory containing `library_system/`:

```bash
python -m library_system.main
```

Sample local credentials:
- Manager: ID `10001`, password `1234`
- Student: ID `20001`, password `1234`
- Operator: ID `30001`, password `1234`

These credentials are for local learning only. Passwords are stored as plain numbers in JSON; do not use this design for real accounts.

## Run tests

```bash
python -m unittest discover -s library_system/tests -v
```

## Porting notes

- Java getters/setters were replaced with Python attributes and a few properties.
- `LibraryManager` remains as a facade delegating to `BookService`, `StudentService`, and `BorrowService`.
- Login state uses an `Enum`.
- JSON conversion is explicit; custom objects and dates are not automatically JSON-serializable.
- Borrow approval checks the request state and inventory before changing the number of copies.
- This is an incremental port, not a complete feature-for-feature parity release. Signup input, manager features, password security, and richer CLI menus remain candidates for the next iteration.
