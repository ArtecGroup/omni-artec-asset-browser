# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from SortOrder from omni.services.browser.asset

import asyncio
from enum import Enum
from typing import Dict, List, Tuple

from fastapi import Depends

from omni.services.core import routers

from .dependencies import get_app_header, get_app_version

from ..store.base import AssetStoreGroupFacility
from ..models import AssetModel, ProviderModel, SearchCriteria, ConfigModel

router = routers.ServiceAPIRouter()
router.dependencies = [Depends(get_app_header), Depends(get_app_version)]


class SortOrder(str, Enum):
    date = "date"
    name = "name"


@router.get("/categories", response_model=Dict[str, Dict])
async def list_categories(
    asset_store: AssetStoreGroupFacility = router.get_facility("asset_store"),
):
    await asyncio.sleep(0)
    return asset_store.get_categories()


@router.post("/search", response_model=Dict[str, Tuple[List[AssetModel], bool]])
async def search(search: SearchCriteria, asset_store: AssetStoreGroupFacility = router.get_facility("asset_store")):
    return await asset_store.search(search, stores=search.vendors, search_timeout=60)


@router.get("/providers", response_model=Dict[str, ProviderModel])
async def list_vendors(
    asset_store: AssetStoreGroupFacility = router.get_facility("asset_store"),
):
    await asyncio.sleep(0)
    return asset_store.get_providers()


@router.post("/config", response_model=None)
async def config(config_params: ConfigModel, asset_store: AssetStoreGroupFacility = router.get_facility("asset_store")):
    await asyncio.sleep(0)
    return asset_store.config(config_params.vendor)
