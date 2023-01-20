import omni.ui as ui
import carb.settings

from typing import Callable
from .style import AUTH_DIALOG_STYLE


class AuthDialog:
    def __init__(self, **kwargs):
        self._window = None
        self._message = None
        self._username = None
        self._password = None
        self._password_overlay = None
        self._remember = None
        self._ok_button = None
        self._cancel_button = None
        self._sub_begin_edit = None

        self._width = kwargs.get("width", 400)
        self._build_ui()

    def _build_ui(self):
        window_flags = (
            ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_POPUP
            | ui.WINDOW_FLAGS_NO_TITLE_BAR
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_BACKGROUND
            | ui.WINDOW_FLAGS_MODAL
        )
        self._window = ui.Window("Authentication", width=self._width, height=0, flags=window_flags)

        with self._window.frame:
            with ui.ZStack(style=AUTH_DIALOG_STYLE):
                ui.Rectangle(style_type_name_override="Window")
                with ui.VStack(style_type_name_override="Dialog", spacing=6):
                    self._message = ui.Label(
                        f"Please login to your account.", height=20, style_type_name_override="Message"
                    )
                    with ui.HStack(height=0):
                        ui.Label("Email:  ", style_type_name_override="Label")
                        self._username = ui.StringField(
                            width=ui.Percent(75), height=20, style_type_name_override="Field"
                        )
                    with ui.HStack(height=0):
                        ui.Label("Password:  ", style_type_name_override="Label")
                        with ui.ZStack(width=ui.Percent(75)):
                            self._password = ui.StringField(
                                height=20, password_mode=True, style_type_name_override="Field"
                            )
                            self._password_overlay = ui.ZStack()
                            with self._password_overlay:
                                ui.Rectangle(style_type_name_override="Field", name="overlay")
                                ui.Label("Invalid credentials.", style_type_name_override="Field", name="warn")
                    with ui.HStack(height=0):
                        ui.Spacer()
                        ui.Label("Remember My Password  ", width=0, height=20, style_type_name_override="Label")
                        self._remember = ui.CheckBox(enabled=True, width=0, style_type_name_override="CheckBox")
                    with ui.HStack(height=20, spacing=4):
                        ui.Spacer()
                        self._okay_button = ui.Button("Okay", width=100, style_type_name_override="Button")
                        self._cancel_button = ui.Button("Cancel", width=100, style_type_name_override="Button")
                    ui.Spacer(height=2)

        def on_begin_edit(_):
            self._password_overlay.visible = False

        self._sub_begin_edit = self._password.model.subscribe_begin_edit_fn(on_begin_edit)

    @property
    def username(self) -> str:
        if self._username:
            return self._username.model.get_value_as_string()
        return ""

    @property
    def password(self) -> str:
        if self._password:
            return self._password.model.get_value_as_string()
        return ""

    def show(self, provider: str, **kwargs):
        def on_okay(dialog, provider, callback: Callable):
            self._save_default_settings(provider)
            if callback:
                callback(dialog)
            else:
                dialog.hide()

        def on_cancel(dialog, provider, callback: Callable):
            if callback:
                callback(dialog)
            else:
                dialog.hide()

        click_okay_handler = kwargs.get("click_okay_handler")
        self._okay_button.set_clicked_fn(lambda: on_okay(self, provider, click_okay_handler))

        click_cancel_handler = kwargs.get("click_cancel_handler")
        self._cancel_button.set_clicked_fn(lambda: on_cancel(self, provider, click_cancel_handler))

        self._message.text = f"Please login to your {provider} account."
        self._load_default_settings(provider)
        self._password_overlay.visible = False
        self._window.visible = True

    def _load_default_settings(self, provider: str):
        settings = carb.settings.get_settings()
        default_settings = settings.get_as_string("/exts/omni.kit.browser.asset_store/appSettings")
        username = settings.get_as_string(f"{default_settings}/providers/{provider}/username")
        password = settings.get_as_string(f"{default_settings}/providers/{provider}/password")
        remember = settings.get_as_bool(f"{default_settings}/providers/remember_password")

        self._username.model.set_value(username)
        self._password.model.set_value(password)
        self._remember.model.set_value(remember)

    def _save_default_settings(self, provider: str):
        settings = carb.settings.get_settings()
        default_settings = settings.get_as_string("/exts/omni.kit.browser.asset_store/appSettings")
        remember = self._remember.model.get_value_as_bool()
        username = self._username.model.get_value_as_string()
        password = self._password.model.get_value_as_string() if remember else ""

        settings.set_string(f"{default_settings}/providers/{provider}/username", username)
        settings.set_string(f"{default_settings}/providers/{provider}/password", password)
        settings.set_bool(f"{default_settings}/providers/remember_password", remember)

    def warn_password(self):
        self._password_overlay.visible = True

    def hide(self):
        self._window.visible = False

    def destroy(self):
        self._message = None
        self._username = None
        self._password = None
        self._password_overlay = None
        self._remember = None
        self._ok_button = None
        self._cancel_button = None
        self._sub_begin_edit = None
        self._window = None
