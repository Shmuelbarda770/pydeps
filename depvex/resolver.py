import importlib.util
import json
import os
import subprocess
import time
import urllib.request

import requests

from depvex.parser import ImportExtractor


class DependencyResolver:
    CAPTIVE_PORTAL_URLS = [
        "http://connectivitycheck.gstatic.com/generate_204",
        "http://clients3.google.com/generate_204",
    ]

    def __init__(self, parser: ImportExtractor | None = None) -> None:
        self.parser = parser or ImportExtractor()

    def internet_check(self, timeout: int = 3) -> bool:
        for url in self.CAPTIVE_PORTAL_URLS:
            try:
                response = requests.get(url, timeout=timeout)
                if response.status_code == 204:
                    return True
            except requests.RequestException:
                pass
        return False

    def is_installed(self, module_name: str) -> bool:
        return importlib.util.find_spec(module_name) is not None

    def get_local_version(self, module_name: str):
        try:
            result = subprocess.check_output(["pip", "show", module_name], text=True)
            for line in result.splitlines():
                if line.startswith("Version:"):
                    return line.split(":", 1)[1].strip()
        except subprocess.SubprocessError:
            return None
        return None

    def get_pypi_version(self, module_name: str):
        try:
            url = f"https://pypi.org/pypi/{module_name}/json"
            with urllib.request.urlopen(url, timeout=3) as response:
                data = json.load(response)
            return data["info"]["version"]
        except (OSError, KeyError, ValueError):
            return None

    def resolve(self, module_name: str, has_net: bool) -> str:
        version = self.get_local_version(module_name)

        if version:
            return f"{module_name}=={version}"

        if has_net:
            latest_version = self.get_pypi_version(module_name)
            if latest_version:
                return f"{module_name}=={latest_version}"
            return module_name

        return module_name

    def write_req(self, lines, path: str = "requirements.txt") -> None:
        with open(path, "w", encoding="utf-8") as handle:
            for line in sorted(set(lines)):
                handle.write(line + "\n")

    def rebuild_requirements(self, root: str = ".", output_path: str | None = None) -> list[str]:
        discovered = set()

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [directory for directory in dirnames if directory not in {".git", "__pycache__", ".venv", "venv", "node_modules"}]

            for filename in filenames:
                if not filename.endswith(".py"):
                    continue

                file_path = os.path.join(dirpath, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as handle:
                        discovered.update(self.parser.extract_imports(handle.read()))
                except (OSError, SyntaxError):
                    continue

        if output_path is None:
            output_path = os.path.join(root, "requirements.txt")

        requirements = []
        has_net = self.internet_check()
        for module_name in sorted(discovered):
            if module_name:
                requirements.append(self.resolve(module_name, has_net))

        self.write_req(requirements, path=output_path)
        return requirements

    def monitor_project(self, module_list, interval: int = 2) -> None:
        last_req = None

        while True:
            has_net = self.internet_check()
            requirements = []

            for module_name in module_list:
                if self.is_installed(module_name):
                    requirements.append(self.resolve(module_name, has_net))

            if requirements != last_req:
                print("\n[depvex] REQUIREMENTS UPDATED")
                for requirement in requirements:
                    print(" ", requirement)

                self.write_req(requirements)
                last_req = requirements

            time.sleep(interval)