# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from BaseAssetStore, AssetStoreGroupFacility from omni.services.browser.asset

import abc
import asyncio
import traceback
import omni.client
import zipfile

from typing import Dict, List, Tuple, Callable

import carb
from omni.services.facilities.base import Facility

from ..models import AssetModel, ProviderModel, SearchCriteria


class BaseAssetStore(Facility, abc.ABC):
    def __init__(self, store_id: str) -> None:
        super().__init__()
        self._store_id = store_id
        self._categories = {}
        self._download_progress: Dict[str, float] = {}

    def authorized(self) -> bool:
        """Override this method to force authentication flow."""
        return True

    async def authenticate(self, username: str, password: str):
        """Override this method to implement authentication method."""
        pass

    @abc.abstractmethod
    async def _search(self, search_criteria: SearchCriteria) -> Tuple[List[AssetModel], bool]:
        """Searches the asset store.

        This function needs to be implemented as part of an implementation of the BaseAssetStore.
        This function is called by the public `search` function that will wrap this function in a timeout.
        """
        pass

    async def search(self, search_criteria: SearchCriteria, search_timeout: int) -> Tuple[List[AssetModel], bool]:
        """Search the asset store

        Will error and stop the search if search_timeout is exceeded

        Args:
            search_criteria (SearchCriteria): Dictionary with support search fields.
            search_timeout (int): Timeout a search after `search_timeout` seconds. (default: 60 seconds)

        Returns:
            List of asset models and if more.

        Raises:
            asyncio.TimeoutError

        """
        return await asyncio.wait_for(self._search(search_criteria), timeout=search_timeout)

    async def _download(self, asset: AssetModel, dest_url: str, on_progress_fn: Callable[[float], None] = None) -> Dict:
        """Default Download handler using omni.client.

        This function needs to be implemented as part of an implementation of the BaseAssetStore.
        This function is called by the public `download` function that will wrap this function in a timeout.
        """
        ret_value = {"url": None}
        if asset and asset.download_url:
            file_name = asset.download_url.split("/")[-1]
            dest_url = f"{dest_url}/{file_name}"
            carb.log_info(f"Download {asset.download_url} to {dest_url}")
            result = await omni.client.copy_async(
                asset.download_url, dest_url, behavior=omni.client.CopyBehavior.OVERWRITE
            )
            ret_value["status"] = result
            if result != omni.client.Result.OK:
                carb.log_error(f"Failed to download {asset.download_url} to {dest_url}")
                return ret_value
            if asset.download_url.lower().endswith(".zip"):
                # unzip
                output_url = dest_url[:-4]
                await omni.client.create_folder_async(output_url)
                carb.log_info(f"Unzip {dest_url} to {output_url}")
                with zipfile.ZipFile(dest_url, "r") as zip_ref:
                    zip_ref.extractall(output_url)
                    dest_url = output_url
            ret_value["url"] = dest_url
        return ret_value

    async def download(
        self, asset: AssetModel, dest_url: str, on_progress_fn: Callable[[float], None] = None, timeout: int = 600
    ) -> Dict:
        """Downloads an asset from the asset store.

        Args:
            asset (AssetModel): The asset descriptor.
            dest_url (str): Url of the destination file.

        Kwargs:
            timeout (int): Timeout a download after this amount of time. (default: 10 mins.)

        Returns:
            Response Dict.

        Raises:
            asyncio.TimeoutError

        """
        self._download_progress[asset.identifier] = 0

        def __on_download_progress(progress):
            self._download_progress[asset.identifier] = progress
            if on_progress_fn:
                on_progress_fn(progress)

        download_future = asyncio.Task(self._download(asset, dest_url, on_progress_fn=__on_download_progress))
        while True:
            last_progress = self._download_progress[asset.identifier]
            done, pending = await asyncio.wait([download_future], timeout=timeout)
            if done:
                return download_future.result()
            else:
                # download not completed
                # if progress changed, continue to wait for completed
                # otherwwise, treat as timeout
                if self._download_progress[asset.identifier] == last_progress:
                    carb.log_warn(f"[{asset.name}]: download timeout")
                    download_future.cancel()
                    return {"status": omni.client.Result.ERROR_ACCESS_LOST}

    def categories(self) -> Dict[str, List[str]]:
        """Return the list of predefined categories."""
        return self._categories

    def id(self) -> str:
        """Return store id."""
        return self._store_id

    def provider(self) -> ProviderModel:
        """Return provider info"""
        return ProviderModel(name=self._store_id)

    def config(self) -> None:
        """Entry point to config the provider"""
        pass


class AssetStoreGroupFacility(Facility):
    def __init__(self):
        self._stores: Dict[str, BaseAssetStore] = {}
        self._updated = True

        super().__init__()

    def register_store(self, name: str, store: BaseAssetStore) -> None:
        self._stores[name] = store
        self._updated = True

    def unregister_store(self, store: BaseAssetStore) -> None:
        self._stores.pop(store.id())
        self._updated = True

    def clear_stores(self) -> None:
        self._stores = {}

    def get_registered_stores(self) -> List[str]:
        """Return list of all registered stores."""
        return list(self._stores.keys())

    def get_store(self, store_name: str) -> BaseAssetStore:
        return self._stores.get(store_name)

    def get_providers(self) -> Dict[str, ProviderModel]:
        providers = {}
        for name, store in self._stores.items():
            providers[store.id()] = store.provider()
        return providers

    def get_categories(self):
        categories = {}
        for store_name, store in self._stores.items():
            categories[store_name] = store.categories()

        return categories

    def config(self, name: str):
        if name in self._stores:
            self._stores[name].config()

    async def search(
        self, search_criteria: SearchCriteria, stores: List[str] = None, search_timeout: int = 60
    ) -> Dict[str, Tuple[List[AssetModel], bool]]:
        stores = stores or self.get_registered_stores()

        queries: Dict[str, asyncio.Future] = {}

        for store_name in stores:
            queries[store_name] = asyncio.ensure_future(
                # Use a deep copy of the ``search_criteria`` model in order to prevent one of the ``AssetStore``'s
                # ``search()`` operation from mutating the object in the body of the function, which would end up
                # affecting the search criterias of downstream ``AssetStore``s:
                self._stores[store_name].search(
                    search_criteria=search_criteria.copy(deep=True), search_timeout=search_timeout
                )
            )

        await asyncio.gather(*queries.values(), return_exceptions=True)

        results = {}
        for store, query in queries.items():
            try:
                results[store] = query.result()
            except Exception:
                carb.log_warn(f"Failed to fetch results for store {store}. Reason:")
                carb.log_warn(traceback.format_exc())

        return results
