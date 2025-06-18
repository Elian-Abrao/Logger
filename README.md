# Logger

This project demonstrates an advanced logging setup.
Run `main.py` for a small demo.

Each execution produces two log files:
- `Logs/<name> - <timestamp>.log` (general info)
- `LogsDEBUG/<name> - <timestamp>.log` (full debug details)

Use `logger.path()` and `logger.debug_path()` to retrieve these paths at runtime.
