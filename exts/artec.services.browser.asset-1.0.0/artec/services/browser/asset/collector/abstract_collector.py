# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from AbstractCollector from omni.services.browser.asset

import abc
from typing import List
from ..models import AssetModel


class AbstractCollector(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    async def collect(self) -> List[AssetModel]:
        """
        Collect assets
        """
        return []
