# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from AssetStore MainNavigationItem

from typing import List, Union
from omni.kit.browser.core import CategoryItem


class MainNavigationItem(CategoryItem):
    def __init__(self, name: str, url: str, provider: Union[str, List[str], None]):
        super().__init__(name)
        self.url = url
        self.thumbnail = None
        self.configurable = False
        self.providers: List[str] = []
        if provider is None:
            self.providers = []
        elif isinstance(provider, str):
            self.providers = [provider]
        else:
            self.providers = provider

    def add_provider(self, provider):
        if provider not in self.providers:
            self.providers.append(provider)
