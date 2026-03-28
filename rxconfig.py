import reflex as rx

config = rx.Config(
    app_name="aiflow_ui",
    db_url="sqlite:///reflex.db",
    telemetry_enabled=False,
    # Skip DB migration check (AIFlow uses its own Alembic with PostgreSQL)
    db_auto_migrate=False,
)
