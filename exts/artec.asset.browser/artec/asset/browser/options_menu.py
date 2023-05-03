# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from AssetStore class AssetOptionsMenu

from omni.kit.browser.core import OptionMenuDescription, OptionsMenu
from .models import AssetStoreModel


class AssetOptionsMenu(OptionsMenu):
    """
    Represent options menu used in asset store.
    """

    def __init__(self, model: AssetStoreModel):
        super().__init__()

        self._model = model
        self._my_assets_window = None
        self._menu_descs = []

    def destroy(self) -> None:
        if self._my_assets_window is not None:
            self._my_assets_window.destroy()
            self._my_assets_window = None
        super().destroy()

    def show(self) -> None:
        if self._options_menu is None:
            for provider, setting in self._model.providers.items():
                if setting["configurable"]:
                    self._menu_descs.append(
                        OptionMenuDescription(
                            f"{provider} Setting", clicked_fn=lambda p=provider: self._model.config_provider(p)
                        )
                    )

        super().show()
