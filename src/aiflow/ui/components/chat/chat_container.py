"""Reusable chat container component."""
import reflex as rx


def message_bubble(msg) -> rx.Component:
    """Single chat message bubble."""
    is_user = msg.role == "user"
    return rx.box(
        rx.markdown(msg.content, size="2"),
        padding="12px 16px",
        border_radius="12px",
        max_width="80%",
        bg=rx.cond(is_user, "blue.50", "gray.50"),
        align_self=rx.cond(is_user, "flex-end", "flex-start"),
        margin_y="4px",
    )


def chat_container(
    messages: list,
    current_input: rx.Var,
    on_send: rx.EventHandler,
    on_input_change: rx.EventHandler,
    is_processing: rx.Var,
    placeholder: str = "Kerem irja be a kerdeset...",
) -> rx.Component:
    """Reusable chat container with message list + input."""
    return rx.vstack(
        # Message list
        rx.box(
            rx.foreach(messages, message_bubble),
            display="flex",
            flex_direction="column",
            overflow_y="auto",
            flex="1",
            padding="16px",
            width="100%",
        ),
        # Input area
        rx.hstack(
            rx.input(
                value=current_input,
                on_change=on_input_change,
                placeholder=placeholder,
                on_key_down=rx.cond(
                    rx.EventChain.key == "Enter",
                    on_send,
                ),
                flex="1",
                size="3",
            ),
            rx.button(
                rx.cond(is_processing, rx.spinner(size="1"), rx.icon("send")),
                on_click=on_send,
                disabled=is_processing,
                size="3",
            ),
            width="100%",
            padding="16px",
        ),
        height="100vh",
        width="100%",
    )
