import omni.ext
import omni.kit.ui

from .window import ArtecCloudWindow, ARTEC_CLOUD_WINDOW_NAME

ASSET_STORE_BROWSER_MENU_PATH = "Window/Browsers/" + ARTEC_CLOUD_WINDOW_NAME
_extension_instance = None


class AssetStoreExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._window = None
        self._menu = omni.kit.ui.get_editor_menu().add_item(
            ASSET_STORE_BROWSER_MENU_PATH, self._on_click, toggle=True, value=True
        )

        self._window = ArtecCloudWindow()
        self._window.set_visibility_changed_fn(self._on_visibility_changed)

        global _extension_instance
        _extension_instance = self

    def on_shutdown(self):
        if self._window is not None:
            self._window.destroy()
            self._window = None

        global _extension_instance
        _extension_instance = None

    def _on_click(self, *args):
        self._window.visible = not self._window.visible

    def _on_visibility_changed(self, visible):
        omni.kit.ui.get_editor_menu().set_value(ASSET_STORE_BROWSER_MENU_PATH, visible)


def get_instance():
    return _extension_instance
