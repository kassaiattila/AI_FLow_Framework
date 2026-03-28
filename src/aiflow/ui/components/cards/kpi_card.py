"""KPI metric card."""
import reflex as rx


def kpi_card(title: str, value: str, subtitle: str = "", color: str = "blue") -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(title, size="1", color="gray"),
            rx.heading(value, size="6", color=f"{color}.9"),
            rx.text(subtitle, size="1", color="gray") if subtitle else rx.fragment(),
            spacing="1",
        ),
        width="200px",
    )
