# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
import importlib
from typing import Optional

import carb
import carb.settings
import carb.tokens

import omni.ext

from omni.services.core import main

from .store.base import AssetStoreGroupFacility, BaseAssetStore

from .services.asset import router

from pathlib import Path

CURRENT_PATH = Path(__file__).parent
ASSETS_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("data").joinpath("assets")

_extension_instance = None


class AssetServiceExtension(omni.ext.IExt):
    """ Asset service extension.
    """

    def on_startup(self, ext_id):
        settings = carb.settings.get_settings()
        ext_name = ext_id.split("-")[0]
        api_version = settings.get(f"exts/{ext_name}/api_version")
        self._base_url = f"/{api_version}/assets"

        self._asset_store_group = AssetStoreGroupFacility()

        router.register_facility("asset_store", self._asset_store_group)
        main.register_router(router, prefix=self._base_url, tags=["assets"])

        global _extension_instance
        _extension_instance = self

    def on_shutdown(self):
        global _extension_instance
        _extension_instance = None

        main.deregister_router(router, prefix=self._base_url)

    def resolve_cls(self, import_path):
        cls_name = import_path.split(".")[-1]
        import_path = import_path.replace(f".{cls_name}", "")
        module = importlib.import_module(import_path)
        return getattr(module, cls_name)

    def register_store(self, asset_provider: BaseAssetStore) -> None:
        self._asset_store_group.register_store(asset_provider.id(), asset_provider)

    def unregister_store(self, asset_store: BaseAssetStore) -> None:
        self._asset_store_group.unregister_store(asset_store)

    def get_store(self, store_name: str) -> BaseAssetStore:
        if store_name:
            return self._asset_store_group.get_store(store_name)
        return None


def get_instance() -> Optional[AssetServiceExtension]:
    return _extension_instance
