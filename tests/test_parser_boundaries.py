import ast
from pathlib import Path

PARSERS_DIR = Path(__file__).parents[1] / "src" / "jav_metadatahub" / "parsers"
FORBIDDEN_IMPORT_PREFIXES = (
    "jav_metadatahub.repositories",
    "jav_metadatahub.services",
)


def test_parsers_do_not_import_repositories_or_services() -> None:
    violations: list[str] = []

    for path in sorted(PARSERS_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(FORBIDDEN_IMPORT_PREFIXES):
                        violations.append(f"{path.relative_to(PARSERS_DIR)} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                if node.module.startswith(FORBIDDEN_IMPORT_PREFIXES):
                    violations.append(f"{path.relative_to(PARSERS_DIR)} imports from {node.module}")

    assert violations == []
