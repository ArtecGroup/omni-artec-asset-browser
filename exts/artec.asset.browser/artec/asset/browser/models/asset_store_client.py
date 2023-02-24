import asyncio
from typing import List, Optional, Dict, Tuple

import carb.settings
from omni.services.client import AsyncClient
from omni.services.core import main

from artec.services.browser.asset import AssetModel


class AssetStoreClient:
    """
    Represent client to asset store service. 
    Args:
        url: Asset service url
    """

    def __init__(self, url: str):
        self._url = url
        self._assets: List[AssetModel] = []

        api_version = carb.settings.get_settings_interface().get("exts/artec.services.browser.asset/api_version")
        self._client = AsyncClient(f"{self._url}/{api_version}", app=main.get_app())

    def destroy(self):
        asyncio.ensure_future(self._stop())

    def list(self, category: str, search_words: Optional[List[str]] = None) -> List[AssetModel]:
        return asyncio.get_event_loop().run_until_complete(self._list_async(category, search_words=search_words))

    async def list_categories_async(self):
        categories = await self._client.assets.categories.get()
        return categories

    async def list_providers_async(self) -> Dict[str, str]:
        return await self._client.assets.providers.get()

    async def config_provider_async(self, provider: str) -> None:
        return await self._client.assets.config.post(vendor=provider)

    async def _list_async(
        self,
        category: Optional[str],
        search_words: Optional[List[str]] = None,
        sort=["name", "asc"],
        page_size=100,
        page_number=1,
        providers=None,
    ) -> Tuple[List[AssetModel], bool]:
        assets = []

        search_args = {
            "page": {"size": page_size, "number": page_number},
            "keywords": search_words,
            "sort": sort,
            "vendors": providers,
        }
        if category:
            search_args["filter"] = {"categories": [category]}

        to_continue = False
        result = await self._client.assets.search.post(**search_args)
        for store in result:
            assets.extend(result[store][0])
            if result[store][1]:
                to_continue = True

        return (assets, to_continue)

    async def _stop(self):
        await self._client.stop_async()
        self._client = None
