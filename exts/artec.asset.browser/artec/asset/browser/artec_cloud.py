# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from SketchFabAssetProvider for asset store

from typing import Dict, List, Tuple, Callable
import carb
import carb.settings

import aiohttp
import asyncio
import omni.client

from urllib.parse import urlparse, urlencode

from artec.services.browser.asset import BaseAssetStore, AssetModel, SearchCriteria, ProviderModel

from pathlib import Path

from .models.asset_fusion import AssetFusion

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
            item_thumbnail = self.thumbnail_url(item.get("preview_presigned_url"))
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
    
    def thumbnail_url(self, url: str) -> str:
        params = {"auth_token": self._auth_token}
        url += ('&' if urlparse(url).query else '?') + urlencode(params)
        return url

    def destroy(self):
        self._auth_params = None

    async def download(
        self, fusion: AssetFusion, dest_url: str, on_progress_fn: Callable[[float], None] = None, timeout: int = 600
    ) -> Dict:
        self._download_progress[fusion.name] = 0

        def __on_download_progress(progress):
            self._download_progress[fusion.name] = progress
            if on_progress_fn:
                on_progress_fn(progress)

        download_future = asyncio.Task(self._download(fusion, dest_url, on_progress_fn=__on_download_progress))
        while True:
            last_progress = self._download_progress[fusion.name]
            done, pending = await asyncio.wait([download_future], timeout=timeout)
            if done:
                return download_future.result()
            else:
                # download not completed
                # if progress changed, continue to wait for completed
                # otherwwise, treat as timeout
                if self._download_progress[fusion.name] == last_progress:
                    carb.log_warn(f"[{fusion.name}]: download timeout")
                    download_future.cancel()
                    return {"status": omni.client.Result.ERROR_ACCESS_LOST}
                
    async def _download(self, fusion: AssetFusion, dest_url: str, on_progress_fn: Callable[[float], None] = None) -> Dict:
        ret_value = {"url": None}
        if fusion and fusion.url:
            file_name = fusion.url.split("/")[-1]
            dest_url = f"{dest_url}/{file_name}"
            carb.log_info(f"Download {fusion.url} to {dest_url}")
            result = await omni.client.copy_async(
                fusion.url, dest_url, behavior=omni.client.CopyBehavior.OVERWRITE
            )
            ret_value["status"] = result
            if result != omni.client.Result.OK:
                carb.log_error(f"Failed to download {fusion.url} to {dest_url}")
                return ret_value
            if fusion.url.lower().endswith(".zip"):
                # unzip
                output_url = dest_url[:-4]
                await omni.client.create_folder_async(output_url)
                carb.log_info(f"Unzip {dest_url} to {output_url}")
                with zipfile.ZipFile(dest_url, "r") as zip_ref:
                    zip_ref.extractall(output_url)
                    dest_url = output_url
            ret_value["url"] = dest_url
        return ret_value