import ast
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
FRAMEWORKS = ('fastapi', 'chromadb', 'openai', 'langgraph', 'langchain', 'langchain_core', 'langchain_openai', 'langchain_google_genai', 'httpx', 'bs4')

def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend((alias.name for alias in node.names))
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules

def _python_files(package: str) -> list[Path]:
    return [path for path in (ROOT / package).rglob('*.py')]

def test_domain_does_not_import_frameworks() -> None:
    forbidden = FRAMEWORKS + ('app.application', 'app.infrastructure', 'app.presentation')
    for path in _python_files('app/domain'):
        for module in _imported_modules(path):
            assert not module.startswith(forbidden), f'{path.name} imports {module}'

def test_application_does_not_import_outer_layers() -> None:
    forbidden = FRAMEWORKS + ('app.infrastructure', 'app.presentation')
    for path in _python_files('app/application'):
        for module in _imported_modules(path):
            assert not module.startswith(forbidden), f'{path.name} imports {module}'
