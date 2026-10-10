"""Write the API schema to docs/openapi.json (the frontend generates its types from it).

CLI: python -m app.export_openapi
"""
import json

from app import config
from app.main import app

PATH = config.REPO_ROOT / "docs" / "openapi.json"


def schema_text() -> str:
    return json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"


def main() -> None:
    PATH.parent.mkdir(exist_ok=True)
    PATH.write_text(schema_text())
    print(f"wrote {PATH}")


if __name__ == "__main__":
    main()
