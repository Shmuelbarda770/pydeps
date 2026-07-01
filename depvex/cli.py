from pathlib import Path
import argparse
import sys

from depvex.watcher import ProjectWatcher
from depvex.resolver import DependencyResolver


class DepvexCLI:
    def __init__(self) -> None:
        self.parser = self._build_parser()

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="depvex")
        subparsers = parser.add_subparsers(dest="command")

        scan_parser = subparsers.add_parser("scan", help="Run a one-time dependency scan and update requirements.txt")
        scan_parser.add_argument("path", nargs="?", default=".")

        check_parser = subparsers.add_parser("check", help="Check whether requirements.txt is up to date")
        check_parser.add_argument("path", nargs="?", default=".")

        watch_parser = subparsers.add_parser("watch", help="Watch project and auto-update requirements.txt")
        watch_parser.add_argument("path", nargs="?", default=".")
        return parser

    def scan(self, path: str) -> int:
        print(f"[depvex] Scanning {path} ...")
        resolver = DependencyResolver()
        resolver.rebuild_requirements(path)
        return 0

    def check(self, path: str) -> int:
        print(f"[depvex] Checking {path} ...")
        resolver = DependencyResolver()
        output_path = Path(path) / "requirements.txt"

        if not output_path.exists():
            return 1

        discovered = set()
        for dirpath, dirnames, filenames in __import__("os").walk(path):
            dirnames[:] = [directory for directory in dirnames if directory not in {".git", "__pycache__", ".venv", "venv", "node_modules"}]
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                file_path = Path(dirpath) / filename
                discovered.update(resolver._get_imports_for_file(str(file_path)))

        expected_requirements = [resolver.resolve(module_name, resolver.internet_check()) for module_name in sorted(discovered) if module_name]
        current_requirements = [line.strip() for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]

        if set(expected_requirements) != set(current_requirements):
            return 1

        return 0

    def watch(self, path: str) -> None:
        print(f"[depvex] Watching {path} ...")

        resolver = DependencyResolver()
        resolver.rebuild_requirements(path)
        ProjectWatcher(path, resolver=resolver).start()

    def run(self, argv: list[str] | None = None) -> int:
        args = self.parser.parse_args(argv or sys.argv[1:])

        if args.command == "scan":
            return self.scan(args.path)

        if args.command == "check":
            return self.check(args.path)

        if args.command == "watch":
            self.watch(args.path)
            return 0

        self.parser.print_help()
        return 1

    def __call__(self, argv: list[str] | None = None) -> int:
        return self.run(argv)


def main(argv: list[str] | None = None) -> int:
    return DepvexCLI().run(argv)