from pathlib import Path
from app.config import GENERATED_PROJECTS_DIR


def get_project_dir(project_name: str) -> Path:
    base = Path(GENERATED_PROJECTS_DIR)
    base.mkdir(parents=True, exist_ok=True)
    project_dir = base / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def write_generated_files(project_name: str, files: dict[str, str]) -> str:
    project_dir = get_project_dir(project_name)

    for relative_path, content in files.items():
        file_path = project_dir / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    return str(project_dir.resolve())