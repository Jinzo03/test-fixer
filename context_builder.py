import ast
from pathlib import Path


class ContextBuilder:
    """Scans local Python imports to collect helper-file contexts."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()

    def _resolve_module(self, module: str | None) -> Path | None:
        """Resolve a dotted Python module to a local .py file or package."""
        if not module:
            return None

        module_path = self.root_dir.joinpath(*module.split("."))

        # module.py
        file_candidate = module_path.with_suffix(".py")
        if file_candidate.is_file():
            return file_candidate.resolve()

        # module/__init__.py
        package_candidate = module_path / "__init__.py"
        if package_candidate.is_file():
            return package_candidate.resolve()

        return None

    def _resolve_relative_import(
        self,
        file_path: Path,
        node: ast.ImportFrom,
    ) -> Path | None:
        """Resolve imports such as `from .utils import foo`."""
        level = node.level
        module = node.module or ""

        # Find the package directory containing file_path.
        base_dir = file_path.parent

        # level=1 means current package, level=2 means parent package, etc.
        for _ in range(max(level - 1, 0)):
            base_dir = base_dir.parent

        if module:
            base_dir = base_dir.joinpath(*module.split("."))

        file_candidate = base_dir.with_suffix(".py")
        if file_candidate.is_file():
            return file_candidate.resolve()

        package_candidate = base_dir / "__init__.py"
        if package_candidate.is_file():
            return package_candidate.resolve()

        return None

    def find_local_imports(self, file_path: Path) -> set[Path]:
        """Parse AST and find project-local Python modules imported by a file."""
        file_path = file_path.resolve()

        if not file_path.is_file():
            return set()

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except (OSError, UnicodeDecodeError, SyntaxError):
            return set()

        local_files: set[Path] = set()

        for node in ast.walk(tree):
            candidate: Path | None = None

            if isinstance(node, ast.ImportFrom):
                if node.level:
                    candidate = self._resolve_relative_import(file_path, node)
                else:
                    candidate = self._resolve_module(node.module)

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    candidate = self._resolve_module(alias.name)

                    if (
                        candidate
                        and candidate != file_path
                        and candidate.is_relative_to(self.root_dir)
                    ):
                        local_files.add(candidate)

        if (
            candidate
            and candidate != file_path
            and candidate.is_relative_to(self.root_dir)
        ):
            local_files.add(candidate)

        return local_files

    def build_context_prompt(
        self,
        target_file: Path,
        test_file: Path,
    ) -> str:
        """Gather imported local files into a structured Markdown block."""
        discovered: set[Path] = set()

        discovered.update(self.find_local_imports(target_file))
        discovered.update(self.find_local_imports(test_file))

        if not discovered:
            return ""

        sections: list[str] = [
            "### Additional Codebase Context (Imported Dependencies):"
        ]

        for dep_path in sorted(discovered):
            try:
                source = dep_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            rel_name = dep_path.relative_to(self.root_dir)

            sections.append(
                f"File: `{rel_name}`\n"
                "```python\n"
                f"{source.rstrip()}\n"
                "```"
            )

        return "\n\n".join(sections)