"""Progress tracking and display."""

import json
from pathlib import Path


def count_passing_tests(project_dir: Path) -> tuple[int, int]:
    """Return (passing_count, total_count) from feature_list.json."""
    tests_file = project_dir / "feature_list.json"
    if not tests_file.exists():
        return 0, 0

    try:
        tests = json.loads(tests_file.read_text())
        total = len(tests)
        passing = sum(1 for t in tests if t.get("passes"))
        return passing, total
    except (json.JSONDecodeError, IOError):
        return 0, 0


def print_session_header(session_num: int, is_initializer: bool) -> None:
    session_type = "INITIALIZER" if is_initializer else "CODING AGENT"
    print("\n" + "=" * 70)
    print(f"  SESSION {session_num}: {session_type}")
    print("=" * 70)
    print()


def print_progress_summary(project_dir: Path) -> None:
    passing, total = count_passing_tests(project_dir)
    if total > 0:
        pct = (passing / total) * 100
        print(f"\nProgress: {passing}/{total} tests passing ({pct:.1f}%)")
    else:
        print("\nProgress: feature_list.json not yet created")
