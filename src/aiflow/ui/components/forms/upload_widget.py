"""Document upload widget for RAG skills."""
import reflex as rx


def upload_widget(
    on_upload: rx.EventHandler,
    accepted_types: list[str] = [".pdf", ".docx", ".txt", ".md"],
) -> rx.Component:
    return rx.upload(
        rx.vstack(
            rx.icon("upload", size=40, color="gray"),
            rx.text("Dokumentumok feltoltese", size="2"),
            rx.text(f"Tamogatott: {', '.join(accepted_types)}", size="1", color="gray"),
            align="center",
            spacing="2",
        ),
        accept={
            "application/pdf": [".pdf"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
            "text/plain": [".txt"],
            "text/markdown": [".md"],
        },
        on_drop=on_upload,
        border="2px dashed #ccc",
        border_radius="8px",
        padding="24px",
        width="100%",
        cursor="pointer",
    )
