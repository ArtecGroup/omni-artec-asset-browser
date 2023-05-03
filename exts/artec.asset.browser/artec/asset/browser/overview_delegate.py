# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from AssetStore class OverviewDelegate

from typing import Optional
import carb.settings
from omni.kit.browser.core import DetailDelegate, CategoryItem


class OverviewDelegate(DetailDelegate):
    def get_label(self, item: CategoryItem) -> Optional[str]:
        return item.name.upper()

    def on_double_click(self, item: CategoryItem) -> None:
        # Show selected category
        settings = carb.settings.get_settings()
        settings.set("/exts/artec.asset.browser/showCategory", item.url)
