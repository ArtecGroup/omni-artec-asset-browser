# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from SketchFabAssetProvider for asset store

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple, Callable
import carb
import carb.settings

import aiohttp
import aiofiles
import asyncio
import omni.client
import omni.kit.asset_converter as converter

from urllib.parse import urlparse, urlencode

from artec.services.browser.asset import BaseAssetStore, AssetModel, SearchCriteria, ProviderModel

from pathlib import Path

from .models.asset_fusion import AssetFusion

SETTING_ROOT = "/exts/artec.asset.browser/"
SETTING_STORE_ENABLE = SETTING_ROOT + "enable"

CURRENT_PATH = Path(__file__).parent
DATA_PATH = CURRENT_PATH.parent.parent.parent.joinpath("data")


class ConversionTaskStatus(Enum):
    ENQUEUED = 1
    IN_PROGRESS = 2
    PROCESSED = 3
    FAILED = -1


@dataclass
class ConversionResult:
    status: ConversionTaskStatus
    download_url: str


async def convert(input_asset_path, output_asset_path):
    task_manager = converter.get_instance()
    task = task_manager.create_converter_task(input_asset_path, output_asset_path, None)
    success = await task.wait_until_finished()
    if not success:
        carb.log_error(f"Conversion failed. Reason: {task.get_error_message()}")


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
            item_thumbnail = self.url_with_token(item.get("preview_presigned_url"))
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

    def url_with_token(self, url: str) -> str:
        params = {"auth_token": self._auth_token}
        url += ('&' if urlparse(url).query else '?') + urlencode(params)
        return url

    def destroy(self):
        self._auth_params = None

    async def download(self, fusion: AssetFusion, dest_path: str,
                       on_progress_fn: Callable[[float], None] = None, timeout: int = 600) -> Dict:
        self._download_progress[fusion.name] = 0
        dest_path = f"{dest_path}/{fusion.name}.obj"
        snapshot_group_id = await self._request_model(fusion)
        while True:
            conversion_result = await self._check_status(fusion, snapshot_group_id)
            if conversion_result.status is ConversionTaskStatus.PROCESSED:
                async with aiohttp.ClientSession() as session:
                    async with session.get(conversion_result.download_url) as response:
                        async with aiofiles.open(dest_path, "wb") as file:
                            await file.write(await response.read())
                        break
            elif conversion_result.status is ConversionTaskStatus.FAILED:
                return {"url": None, "status": omni.client.Result.ERROR}

        usd_path = dest_path.replace('.obj', '.usd')
        asyncio.ensure_future(convert(dest_path, usd_path))
        return {"url": usd_path, "status": omni.client.Result.OK}

    async def _check_status(self, fusion: AssetFusion, snapshot_group_id):
        params = {
            "auth_token": self._auth_token,
            "snapshot_group_id": snapshot_group_id
        }
        slug = fusion.asset.asset_model["product_url"].split("/")[-1]
        url = f"https://staging-cloud.artec3d.com/api/omni/1.0/projects/{slug}/conversion_status"
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, params=params) as response:
                decoded_response = await response.json()
        result = ConversionResult(ConversionTaskStatus(int(decoded_response["project"]["conversion_status"])),
                                  decoded_response["project"]["download_url"])
        return result

    async def _request_model(self, fusion: AssetFusion):
        async with aiohttp.ClientSession() as session:
            async with session.get(url=self.url_with_token(fusion.url)) as response:
                results = await response.json()
        return results["project"]["snapshot_group_id"]
