from typing import Callable

from omni import ui
from .style import EMPTY_NOTIFICATION_STYLE, ICON_PATH


class SearchNotification:
    """
    When no results searched, show notification. 
    """

    def __init__(self, clear_search_fn: Callable[[None], None]):
        self._clear_search_fn = clear_search_fn
        self._build_ui()

    def _build_ui(self):
        self._container = ui.ZStack(style=EMPTY_NOTIFICATION_STYLE)
        with self._container:
            ui.Rectangle(style_type_name_override="EmptyNotification.Frame")
            with ui.VStack(spacing=10):
                ui.Spacer()
                with ui.HStack(height=0):
                    ui.Spacer()
                    ui.ImageWithProvider(
                        f"{ICON_PATH}/search.png",
                        width=90,
                        height=60,
                        fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                        style_type_name_override="EmptyNotification.Image",
                    )
                    ui.Spacer()
                self._message_label = ui.Label(
                    "not found.",
                    height=0,
                    alignment=ui.Alignment.CENTER,
                    style_type_name_override="EmptyNotification.Label",
                )
                self._clear_container = ui.HStack(height=24)
                with self._clear_container:
                    ui.Spacer()
                    ui.Button(
                        "Click to clear search",
                        width=192,
                        mouse_pressed_fn=lambda x, y, btn, a: self._clear_search_fn(),
                        style_type_name_override="EmptyNotification.Button",
                    )
                    ui.Spacer()
                ui.Spacer()

    @property
    def visible(self) -> bool:
        return self._container.visible

    @visible.setter
    def visible(self, value) -> None:
        self._container.visible = value

    def set_message(self, message: str, show_clear: bool = True) -> None:
        self._message_label.text = message
        self._clear_container.visible = show_clear
