"""ASZF RAG Chat admin/config page."""
import reflex as rx
from src.aiflow.ui.components.forms.upload_widget import upload_widget
from src.aiflow.ui.components.cards.kpi_card import kpi_card


class AszfAdminState(rx.State):
    collection: str = "azhu-aszf-2024"
    document_count: int = 0
    chunk_count: int = 0
    last_ingest: str = "-"
    upload_status: str = ""


def aszf_admin_page() -> rx.Component:
    return rx.vstack(
        rx.heading("ASZF RAG - Dokumentum Kezeles", size="5"),
        # KPI cards
        rx.hstack(
            kpi_card("Dokumentumok", str(AszfAdminState.document_count)),
            kpi_card("Chunk-ok", str(AszfAdminState.chunk_count)),
            kpi_card("Utolso feldolgozas", AszfAdminState.last_ingest),
            spacing="4",
        ),
        # Upload
        rx.heading("Dokumentum feltoltes", size="4"),
        upload_widget(on_upload=rx.window_alert("Upload - TODO")),
        # Status
        rx.cond(AszfAdminState.upload_status != "",
                rx.callout(AszfAdminState.upload_status, icon="info")),
        spacing="4",
        padding="24px",
        width="100%",
        max_width="800px",
        margin="0 auto",
    )
