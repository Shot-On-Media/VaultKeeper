from __future__ import annotations

from pathlib import Path


def test_alembic_env_does_not_interpolate_database_url() -> None:
    env_path = Path("alembic/env.py")

    content = env_path.read_text(encoding="utf-8")

    assert 'config.set_main_option("sqlalchemy.url"' not in content
    assert "create_engine(" in content
