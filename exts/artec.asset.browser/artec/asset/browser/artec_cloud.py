# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""SketchFab asset store implementation."""

from typing import Dict, List, Optional, Union, Tuple, Callable
import carb
import carb.settings

import os
import aiohttp
import asyncio
import omni.client

from artec.services.browser.asset import BaseAssetStore, AssetModel, SearchCriteria, ProviderModel

from pathlib import Path

SETTING_ROOT = "/exts/artec.asset.browser/"
SETTING_STORE_ENABLE = SETTING_ROOT + "enable"

CURRENT_PATH = Path(__file__).parent
DATA_PATH = CURRENT_PATH.parent.parent.parent.joinpath("data")

class ArtecCloudAssetProvider(BaseAssetStore):
    """
    SketchFab asset provider implementation.

    For documentation on the search API, see the online interactive API at:
    https://docs.sketchfab.com/data-api/v3/index.html#!/search/get_v3_search_type_models

    .. note:

       SketchFab does not return search results in no search query has been provided. In other words, navigating through
       the pre-defined categories will not display any results from SketchFab, as no search terms have been submitted in
       that context.

    """

    def __init__(self) -> None:
        """
        Constructor.
        Returns:
            None

        """
        settings = carb.settings.get_settings()
        self._provider_id = settings.get_as_string(SETTING_ROOT + "providerId")
        super().__init__(store_id=self._provider_id)

        self._keep_page_size = settings.get_as_bool(SETTING_ROOT + "keepOriginalPageSize")
        self._max_count_per_page = settings.get_as_int(SETTING_ROOT + "maxCountPerPage")
        self._min_thumbnail_size = settings.get_as_int(SETTING_ROOT + "minThumbnailSize")
        self._search_url = settings.get_as_string(SETTING_ROOT + "cloudSearchUrl") # ARTEC_CLOUD
        self._auth_token = None
        self._models_url = settings.get_as_string(SETTING_ROOT + "modelsUrl")
        self._authorize_url = settings.get_as_string(SETTING_ROOT + "authorizeUrl")
        self._access_token_url = settings.get_as_string(SETTING_ROOT + "accessTokenUrl") # INFO: from constants
        self._client_id = settings.get_as_string(SETTING_ROOT + "clientId")  # INFO: from constants
        self._client_secret = settings.get_as_string(SETTING_ROOT + "clientSecret")
        self._auth_params = None

    def provider(self) -> ProviderModel:
        """Return provider info"""
        return ProviderModel(
            name=self._store_id, icon=f"{DATA_PATH}/artec_cloud.png", enable_setting=SETTING_STORE_ENABLE
        )
    
    # def set_auth_token(self, auth_token: str): # WIP under review
    #     self._auth_token = self._auth_params.get('auth_token', None)

    def authorized(self) -> bool: # WIP working
        if self._auth_params:
            self._auth_token = self._auth_params.get('auth_token', None)
            return self._auth_params.get('auth_token', None)

    async def authenticate(self, username: str, password: str): # WIP working
        params = { "user[email]": username, "user[password]": password }
        async with aiohttp.ClientSession() as session:
            async with session.post(self._authorize_url, params=params) as response:  
                self._auth_params = await response.json()

    def get_access_token(self) -> str:
        if self._auth_params:
            return self._auth_params.get("access_token", None)
        return None

    async def _search(self, search_criteria: SearchCriteria) -> Tuple[List[AssetModel], bool]:
        assets: List[AssetModel] = []

        if self._keep_page_size:
            required_count = (
                search_criteria.page.size
                if search_criteria.page.size < self._max_count_per_page
                else self._max_count_per_page
            )
        else:
            required_count = search_criteria.page.size

        params = {
            "type": "models",
            "auth_token": self._auth_token,
            "cursor": (search_criteria.page.number - 1) * required_count,
            "sort_field": "",
            "sort_direction": "",
            "term": "",
            "filters": ""
        }
        
        if search_criteria.sort:
            params['sort_field'], params['sort_direction'] = search_criteria.sort
    
        if search_criteria.keywords:
            params["term"] = " ".join(search_criteria.keywords)

        if search_criteria.filter.categories:
            category = self._pick_category(categories=search_criteria.filter.categories)
            if category:
                params["filters"] = category.lower().replace(" ", "_")

        # The SketchFab API limits the number of search results per page to at most 24
        to_continue = True
        while required_count > 0:
            params["count"] = min(self._max_count_per_page, required_count)
            (page_assets, to_continue) = await self._search_one_page(params)
            if page_assets:
                params["cursor"] += params["count"]
                required_count -= params["count"]
                assets.extend(page_assets)
                if not to_continue:
                    break
            else:
                break

        return (assets, to_continue)

    async def _search_one_page(self, params: Dict) -> Tuple[List[AssetModel], bool]:
        """
        Search one page. Max 24 assets.
        Args:
            params (Dict): Search parameters.
        Returns:
            List[AssetModel]: List of searched assets.
            bool: True means more results to be searched. False means end of search.
        """
        to_continue = False
        items = []
        async with aiohttp.ClientSession() as session:
            async with session.get(self._search_url, params=params) as response:
                results = await response.json()
                # cursors = results.get("cursors", {})
                # If no more resutls
                # to_continue = cursors["next"] is not None
                items = results.get("projects", [])

        assets: List[AssetModel] = []
        
        for item in items:
            item_categories = item.get("categories", [])
            item_thumbnail = item.get('preview_presigned_url')
            # TODO: Download url goes here
            if item.get("isDownloadable"):
                download_url = f"{self._models_url}/{item.get('uid')}/download"
            else:
                download_url = ""
            if item_thumbnail is not None:
                assets.append(
                    AssetModel(
                        identifier=item.get("id"),
                        name=item.get("name"),
                        version="",
                        published_at=item.get("created_at"),
                        categories=item_categories,
                        tags=[], # item_tags,
                        vendor=self._provider_id,
                        download_url=item.get("download_url", ""),
                        product_url=item.get("viewer_url", ""),
                        thumbnail=item_thumbnail, # URL 
                        user=item.get("user"),
                        fusions=item.get("fusions", ""),
                    )
                )

        return (assets, to_continue)

    def _sanitize_categories(self, categories: List[str]) -> List[str]:
        """
        Sanitize the given list of ``SearchCriteria`` categories.

        Args:
            categories (List[str]): List of ``SearchCriteria`` categories to sanitize.

        Returns:
            List[str]: Sanitized category names from the given list of categories.

        """
        sanitized_categories: List[str] = []
        for category in categories:
            if category.startswith("/"):
                category = category[1:]
            category_keywords = category.split("/")
            sanitized_categories.extend(category_keywords)
        return sanitized_categories

    def _pick_category(self, categories: List[str]) -> Optional[str]:
        """
        Pick the most appropriate category from the list of ``SearchCriteria`` categories.

        Args:
            categories (List[str]): List of ``SearchCriteria`` categories from which to pick the most appropriate
                category for a search.

        Returns:
            Optional[str]: The most appropriate category from the given list of ``SearchCriteria`` categories, or
                ``None`` if no category could be identified.

        """
        sanitized_categories = self._sanitize_categories(categories=categories)
        if sanitized_categories:
            return sanitized_categories[-1]
        return None

    def _pick_most_appropriate_thumbnail(self, thumbnails: List[Dict[str, Union[str, int]]]) -> Optional[str]:
        """
        Pick the most appropriate thumbnail URL from the list of provided image metadata abot the asset.

        Args:
            thumbnails (): List of image metadata about the asset.

        Returns:
            Optional[str]: The URL of the image thumbnail to use for the asset, or ``None`` if no suitable thumbnail was
                found.

        """
        high_res_thumbnails: List[Dict[str, Union[str, int]]] = []
        low_res_thumbnails: List[Dict[str, Union[str, int]]] = []

        # Sort the thumbnails in 2 buckets (whether higher resolution than desired, or lower than desired):
        for thumbnail in thumbnails:
            thumbnail_width: Optional[int] = thumbnail.get("width")
            thumbnail_height: Optional[int] = thumbnail.get("height")

            if thumbnail_width is not None and thumbnail_height is not None:
                if thumbnail_width >= self._min_thumbnail_size and thumbnail_height >= self._min_thumbnail_size:
                    high_res_thumbnails.append(thumbnail)
                else:
                    low_res_thumbnails.append(thumbnail)

        # Pick the most appropriate thumbnail within the list of high-res candidates:
        if high_res_thumbnails:
            candidate_thumbnail: Dict[str, Union[str, int]] = high_res_thumbnails[0]

            for thumbnail in high_res_thumbnails:
                if thumbnail.get("width") < candidate_thumbnail.get("width") and thumbnail.get(
                    "height"
                ) < candidate_thumbnail.get("height"):
                    candidate_thumbnail = thumbnail

            return candidate_thumbnail.get("url")

        # Pick the largest thumbnail within the list of low-res candidates:
        if low_res_thumbnails:
            candidate_thumbnail: Dict[str, Union[str, int]] = low_res_thumbnails[0]

            for thumbnail in low_res_thumbnails:
                if thumbnail.get("width") > candidate_thumbnail.get("width") and thumbnail.get(
                    "height"
                ) > candidate_thumbnail.get("height"):
                    candidate_thumbnail = thumbnail

            return candidate_thumbnail.get("url")

        return None

    async def _download(self, asset: AssetModel, dest_url: str, on_progress_fn: Callable[[float], None] = None) -> Dict:
        """ Downloads an asset from the asset store.

            This function needs to be implemented as part of an implementation of the BaseAssetStore.
            This function is called by the public `download` function that will wrap this function in a timeout.
        """
        ret_value = {"url": None}
        if not (asset and asset.download_url):
            ret_value["status"] = omni.client.Result.ERROR_NOT_FOUND
            return ret_value

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": "Bearer %s" % self.get_access_token()}
            async with session.get(asset.download_url, headers=headers) as response:
                results = await response.json()

            # Parse downloaded response; see https://sketchfab.com/developers/download-api/downloading-models
            if "usdz" in results:
                download_url = results["usdz"].get("url")
            else:
                ret_value["status"] = omni.client.Result.ERROR_NOT_FOUND
                carb.log_error(f"[{asset.name}] Invalid download url: {asset.download_url}!")
                carb.log_info(f"addtional result: {results}")
                return ret_value

            content = bytearray()
            # Download content from the given url
            downloaded = 0
            async with session.get(download_url) as response:
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

            if response.ok:
                # Write to destination
                filename = os.path.basename(download_url.split("?")[0])
                dest_url = f"{dest_url}/{filename}"
                (result, list_entry) = await omni.client.stat_async(dest_url)
                if result == omni.client.Result.OK:
                    # If dest file already exists, use asset identifier in filename to different
                    dest_url = dest_url[:-5] + "_" + str(asset.identifier) + ".usdz"
                ret_value["status"] = await omni.client.write_file_async(dest_url, content)
                ret_value["url"] = dest_url
            else:
                carb.log_error(f"[{asset.name}] access denied: {download_url}")
                ret_value["status"] = omni.client.Result.ERROR_ACCESS_DENIED

        return ret_value

    def destroy(self):
        self._auth_params = None