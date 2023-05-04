# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from AbstractCollector from omni.services.browser.asset

from typing import List, Optional, Tuple, Callable

import carb
import omni.client

from ..models import AssetModel
from .abstract_collector import AbstractCollector

THUMBNAIL_PATH = ".thumbs"
THUMBNAIL_SIZE = 256
THUMBNAIL_FULL_PATH = f"{THUMBNAIL_PATH}/{THUMBNAIL_SIZE}x{THUMBNAIL_SIZE}/"


class S3Collector(AbstractCollector):
    def __init__(
        self, url: str, vendor: str, filter_file_suffixes: Optional[List[str]] = [".usd", ".usda", ".usdc", ".usdz"]
    ) -> None:
        self._url = url
        if self._url.endswith("/"):
            self._url = self._url[:-1]
        self._filter_file_suffixes = filter_file_suffixes
        self._vendor = vendor
        self._asset_models = []

        super().__init__()

    async def collect(
        self, default_thumbnail=None, on_folder_done_fn: Callable[[str, List[AssetModel]], None] = None
    ) -> List[AssetModel]:
        await self._traverse_folder_async(
            self._url, default_thumbnail=default_thumbnail, on_folder_done_fn=on_folder_done_fn
        )
        self._asset_models = [asset for asset in self._asset_models if asset.thumbnail != ""]
        return self._asset_models

    async def _traverse_folder_async(
        self,
        url: str,
        recurse: bool = True,
        default_thumbnail=None,
        on_folder_done_fn: Callable[[str, List[AssetModel]], None] = None,
    ):
        """Traverse folder to retreive assets and thumbnails"""
        if not url.endswith("/"):
            url += "/"

        entries = await self._list_folder_async(url)
        if entries:
            thumbnail_path = None
            folder_asset_models = []
            for entry in entries:
                path = omni.client.combine_urls(url, entry.relative_path)
                #  "\" used in local path, convert to "/"
                path = path.replace("\\", "/")
                if entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN:
                    if recurse:
                        dirs = path.split("/")
                        sub_folder_name = dirs[-1]
                        if sub_folder_name == THUMBNAIL_PATH:
                            thumbnail_path = omni.client.combine_urls(url, THUMBNAIL_FULL_PATH)
                        else:
                            await self._traverse_folder_async(
                                path,
                                recurse=recurse,
                                default_thumbnail=default_thumbnail,
                                on_folder_done_fn=on_folder_done_fn,
                            )
                else:
                    asset_model = self._add_asset_model(url, entry, default_thumbnail=default_thumbnail)
                    if asset_model is not None:
                        folder_asset_models.append(asset_model)

            if thumbnail_path is not None:
                # Only verify assets in same folder
                await self._list_thumbnails(thumbnail_path, folder_asset_models)

            if folder_asset_models and on_folder_done_fn:
                on_folder_done_fn(url, folder_asset_models)

    async def _list_folder_async(self, url: str) -> Optional[Tuple[omni.client.ListEntry]]:
        """List files on a s3 server folder"""
        try:
            (result, entries) = await omni.client.list_async(url)
            if result == omni.client.Result.OK:
                return entries
            else:
                carb.log_warn(f"Failed to access {url}")
                return None
        except Exception as e:
            carb.log_error(str(e))
            return None

    def _add_asset_model(self, url: str, entry: omni.client.ListEntry, default_thumbnail=None) -> Optional[AssetModel]:
        file_name = entry.relative_path
        if self._filter_file_suffixes is not None:
            pos = file_name.rfind(".")
            file_suffix = file_name[pos:].lower()
            if file_suffix not in self._filter_file_suffixes:
                return None

        # Use last path in url as first path of category url
        pos = self._url.rfind("/")
        if pos <= 0:
            pos = 0
        category = url[pos:]

        if category[0] == "/":
            category = category[1:]
        if category and category[-1] == "/":
            category = category[:-1]

        # To match search by category, ignore unnecessary sub folders in category url
        sub_categories = category.split("/")[0:3]
        category = "/".join(sub_categories)

        # TODO: identifier/version/tags need to be comfirmed
        asset_model = AssetModel(
            identifier=entry.hash or hash(url + entry.relative_path),
            name=file_name,
            version=entry.version or "",
            published_at=entry.modified_time.timestamp(),
            categories=[category],
            tags=[],
            vendor=self._vendor,
            download_url=url + entry.relative_path,
            product_url="",
            price=0,
            thumbnail=default_thumbnail or "",  # Fill it later
            user=entry.user or "",
        )
        self._asset_models.append(asset_model)
        return asset_model

    async def _list_thumbnails(self, url: str, folder_assset_models: List[AssetModel]) -> None:
        if len(folder_assset_models) == 0:
            return

        entries = await self._list_folder_async(url)
        if entries:
            for entry in entries:
                thumbnail_name = entry.relative_path[:-4]
                for asset_model in folder_assset_models:
                    if thumbnail_name == asset_model.name or thumbnail_name == asset_model.name + ".auto":
                        asset_model.thumbnail = omni.client.combine_urls(url, entry.relative_path)
                        break
