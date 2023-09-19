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
from pathlib import Path
from typing import Callable, Optional, Tuple, Dict, List
import tempfile
from time import time
import zipfile

import aiohttp
import aiofiles
import carb
import carb.settings
import omni.client
import omni.kit.asset_converter as converter
from urllib.parse import urlparse, urlencode

from artec.services.browser.asset import BaseAssetStore, AssetModel, SearchCriteria, ProviderModel
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


class ArtecCloudAssetProvider(BaseAssetStore):
    def __init__(self) -> None:
        settings = carb.settings.get_settings()
        self._provider_id = settings.get_as_string(SETTING_ROOT + "providerId")
        super().__init__(store_id=self._provider_id)

        self._max_count_per_page = settings.get_as_int(SETTING_ROOT + "maxCountPerPage")
        self._search_url = settings.get_as_string(SETTING_ROOT + "cloudSearchUrl")
        self._auth_token = None
        self._authorize_url = settings.get_as_string(SETTING_ROOT + "authorizeUrl")
        self._auth_params: Dict = {}

    def provider(self) -> ProviderModel:
        return ProviderModel(
            name=self._store_id, icon=f"{DATA_PATH}/artec_cloud.png", enable_setting=SETTING_STORE_ENABLE
        )

    def authorized(self) -> bool:
        return self._auth_token is not None

    async def authenticate(self, username: str, password: str):
        params = {"user[email]": username, "user[password]": password}
        async with aiohttp.ClientSession() as session:
            async with session.post(self._authorize_url, params=params) as response:
                self._auth_params = await response.json()
                self._auth_token = self._auth_params.get("auth_token")

    async def _search(self, search_criteria: SearchCriteria) -> Tuple[List[AssetModel], bool]:
        assets: List[AssetModel] = []

        params = {
            "auth_token": self._auth_token,
            "sort_field": "",
            "sort_direction": "",
            "term": "",
            "slug": "",
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
                params["slug"] = category

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
        if not self.authorized():
            return ([], False)
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

        to_continue = meta["total_count"] > meta["current_page"] * meta["per_page"]
        return (assets, to_continue)

    def url_with_token(self, url: str) -> str:
        params = {"auth_token": self._auth_token}
        url += ('&' if urlparse(url).query else '?') + urlencode(params)
        return url

    def destroy(self):
        self._auth_params = {}

    async def download(self, fusion: AssetFusion, dest_path: str,
                       on_progress_fn: Optional[Callable[[float], None]] = None, timeout: int = 600,
                       on_prepared_fn: Optional[Callable[[float], None]] = None) -> Dict:
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_file_path = Path(tmp_dir) / f"{fusion.name}.zip"
            snapshot_group_id, eta = await self._request_model(fusion)
            conversion_start_time = time()

            while True:
                if on_progress_fn:
                    on_progress_fn(min((time() - conversion_start_time) / eta, 1))
                conversion_result = await self._check_status(fusion, snapshot_group_id)
                if conversion_result.status is ConversionTaskStatus.PROCESSED:
                    if on_prepared_fn:
                        on_prepared_fn()
                    async with aiohttp.ClientSession() as session:
                        content = bytearray()
                        downloaded = 0
                        async with session.get(conversion_result.download_url) as response:
                            size = int(response.headers.get("content-length", 0))
                            if size > 0:
                                async for chunk in response.content.iter_chunked(1024 * 512):
                                    content.extend(chunk)
                                    downloaded += len(chunk)
                                    if on_progress_fn:
                                        on_progress_fn(float(downloaded) / size)
                            else:
                                if on_progress_fn:
                                    on_progress_fn(0)
                                content = await response.read()
                                if on_progress_fn:
                                    on_progress_fn(1)
                    async with aiofiles.open(zip_file_path, "wb") as file:
                        await file.write(content)
                    break
                elif conversion_result.status is ConversionTaskStatus.FAILED:
                    return {"url": None, "status": omni.client.Result.ERROR}

            # unzip
            output_path = zip_file_path.parent / fusion.name
            await self._extract_zip(zip_file_path, output_path)

            # convert model
            try:
                obj_path = next(output_path.glob("**/*.obj"))
            except StopIteration:
                return {"url": None, "status": omni.client.Result.ERROR}

            converted_project_path = zip_file_path.parent / f"{obj_path.parent.name}-converted"
            usd_path = converted_project_path / f"{obj_path.stem}.usd"
            await omni.client.create_folder_async(str(converted_project_path))
            if not await self.convert(obj_path, usd_path):
                return {"url": None, "status": omni.client.Result.ERROR}

            # prepare usdz
            usdz_path = Path(dest_path) / f"{usd_path.name}z"
            with zipfile.ZipFile(usdz_path, "w") as archive:
                # usd file should be first in the USDZ package
                archive.write(usd_path, arcname=usd_path.name)
                for file_path in usd_path.parent.glob("**/*"):
                    if file_path != usd_path:
                        archive.write(file_path, arcname=file_path.relative_to(usd_path.parent))

            await self._download_thumbnail(usdz_path, fusion.thumbnail_url)

        return {"url": str(usdz_path), "status": omni.client.Result.OK}

    async def _download_thumbnail(self, usd_path: Path, thumbnail_url: str):
        thumbnail_out_dir_path = usd_path.parent / ".thumbs" / "256x256"
        await omni.client.create_folder_async(str(thumbnail_out_dir_path))
        thumbnail_out_path = thumbnail_out_dir_path / f"{Path(usd_path).name}.png"
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url_with_token(thumbnail_url)) as response:
                async with aiofiles.open(thumbnail_out_path, "wb") as file:
                    await file.write(await response.read())

    @staticmethod
    async def convert(input_asset_path: Path, output_asset_path: Path) -> bool:
        task_manager = converter.get_instance()
        task = task_manager.create_converter_task(str(input_asset_path), str(output_asset_path), None)
        success = await task.wait_until_finished()
        if not success:
            carb.log_error(f"Conversion failed. Reason: {task.get_error_message()}")
            return False
        return True

    @staticmethod
    async def _extract_zip(input_path, output_path):
        await omni.client.create_folder_async(str(output_path))
        with zipfile.ZipFile(input_path, "r") as zip_ref:
            zip_ref.extractall(output_path)

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
        return results["project"]["snapshot_group_id"], results["project"]["eta"]
