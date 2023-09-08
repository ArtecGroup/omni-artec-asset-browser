# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from AssetStore class AssetStoreExtension

import omni.ext
import omni.kit.ui

from .window import ArtecCloudWindow, ARTEC_CLOUD_WINDOW_NAME
from .artec_cloud import ArtecCloudAssetProvider
from artec.services.browser.asset import get_instance as get_asset_services
from artec.services.browser.asset.store.local.local import LocalFolderAssetProvider

ARTEC_CLOUD_BROWSER_MENU_PATH = "Window/Browsers/" + ARTEC_CLOUD_WINDOW_NAME
_extension_instance = None


class ArtecAssetBrowserExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._window = None
        self._menu = omni.kit.ui.get_editor_menu().add_item(
            ARTEC_CLOUD_BROWSER_MENU_PATH, self._on_click, toggle=True, value=True
        )

        self._window = ArtecCloudWindow()
        self._window.set_visibility_changed_fn(self._on_visibility_changed)

        global _extension_instance
        _extension_instance = self

        self._asset_provider = ArtecCloudAssetProvider()
        self._asset_provider_local = LocalFolderAssetProvider()
        self._asset_service = get_asset_services()
        self._asset_service.register_store(self._asset_provider)
        self._asset_service.register_store(self._asset_provider_local)

        _extension_instance

    def on_shutdown(self):
        self._asset_service.unregister_store(self._asset_provider)
        self._asset_service.unregister_store(self._asset_provider_local)
        self._asset_provider = None
        self._asset_provider_local = None
        self._asset_service = None

        if self._window is not None:
            self._window.destroy()
            self._window = None

        global _extension_instance
        _extension_instance = None

    def _on_click(self, *args):
        self._window.visible = not self._window.visible

    def _on_visibility_changed(self, visible):
        omni.kit.ui.get_editor_menu().set_value(ARTEC_CLOUD_BROWSER_MENU_PATH, visible)
