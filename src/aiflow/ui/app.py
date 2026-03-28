"""AIFlow Reflex app factory."""
import reflex as rx


def create_app() -> rx.App:
    """Create the AIFlow Reflex application."""
    app = rx.App(
        theme=rx.theme(
            appearance="light",
            accent_color="blue",
        ),
    )
    return app
