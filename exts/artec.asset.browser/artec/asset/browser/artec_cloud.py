# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from SketchFabAssetProvider for asset store

from typing import Dict, List, Tuple
import carb
import carb.settings

import aiohttp

from artec.services.browser.asset import BaseAssetStore, AssetModel, SearchCriteria, ProviderModel

from pathlib import Path

SETTING_ROOT = "/exts/artec.asset.browser/"
SETTING_STORE_ENABLE = SETTING_ROOT + "enable"

CURRENT_PATH = Path(__file__).parent
DATA_PATH = CURRENT_PATH.parent.parent.parent.joinpath("data")


class ArtecCloudAssetProvider(BaseAssetStore):
    def __init__(self) -> None:
        settings = carb.settings.get_settings()
        self._provider_id = settings.get_as_string(SETTING_ROOT + "providerId")
        super().__init__(store_id=self._provider_id)

        self._max_count_per_page = settings.get_as_int(SETTING_ROOT + "maxCountPerPage")
        self._search_url = settings.get_as_string(SETTING_ROOT + "cloudSearchUrl")
        self._auth_token = None
        self._authorize_url = settings.get_as_string(SETTING_ROOT + "authorizeUrl")
        self._auth_params = None

    def provider(self) -> ProviderModel:
        return ProviderModel(
            name=self._store_id, icon=f"{DATA_PATH}/artec_cloud.png", enable_setting=SETTING_STORE_ENABLE
        )

    def authorized(self) -> bool:
        if self._auth_params:
            self._auth_token = self._auth_params.get("auth_token", None)
            return self._auth_params.get("auth_token", None)

    async def authenticate(self, username: str, password: str):
        params = {"user[email]": username, "user[password]": password}
        async with aiohttp.ClientSession() as session:
            async with session.post(self._authorize_url, params=params) as response:
                self._auth_params = await response.json()

    def get_access_token(self) -> str:
        if self._auth_params:
            return self._auth_params.get("access_token", None)
        return None

    async def _search(self, search_criteria: SearchCriteria) -> Tuple[List[AssetModel], bool]:
        assets: List[AssetModel] = []

        params = {
            "auth_token": self._auth_token,
            "sort_field": "",
            "sort_direction": "",
            "term": "",
            "filters": "",
            "per_page": self._max_count_per_page,
            "page": 0,
        }

        if search_criteria.sort:
            params["sort_field"], params["sort_direction"] = search_criteria.sort

        if search_criteria.keywords:
            params["term"] = " ".join(search_criteria.keywords)

        if search_criteria.filter.categories:
            category = search_criteria.filter.categories[-1]
            if category:
                params["filters"] = category.lower().replace(" ", "_")

        to_continue = True
        while to_continue:
            params["page"] += 1
            (page_assets, to_continue) = await self._search_one_page(params)

            if page_assets:
                assets.extend(page_assets)
                if not to_continue:
                    break
            else:
                break

        return (assets, to_continue)

    async def _search_one_page(self, params: Dict) -> Tuple[List[AssetModel], bool]:
        items = []
        meta = {}

        async with aiohttp.ClientSession() as session:
            async with session.get(self._search_url, params=params) as response:
                results = await response.json()
                items = results.get("projects", [])
                meta = results.get("meta")

        assets: List[AssetModel] = []

        for item in items:
            item_categories = item.get("categories", [])
            item_thumbnail = item.get("preview_presigned_url")
            if item_thumbnail is not None:
                assets.append(
                    AssetModel(
                        identifier=item.get("id"),
                        name=item.get("name"),
                        version="",
                        published_at=item.get("created_at"),
                        categories=item_categories,
                        tags=[],
                        vendor=self._provider_id,
                        download_url=item.get("download_url", ""),
                        product_url=item.get("viewer_url", ""),
                        thumbnail=item_thumbnail,
                        user=item.get("user"),
                        fusions=item.get("fusions", ""),
                    )
                )

        to_continue = meta.get("total_count") > meta.get("current_page") * meta.get("per_page")
        return (assets, to_continue)

    def destroy(self):
        self._auth_params = None
