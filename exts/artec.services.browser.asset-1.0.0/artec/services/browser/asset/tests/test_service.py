# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
import carb.settings
import omni.kit.test

from omni.services.client import AsyncClient
from omni.services.core import main

from ..models import SearchCriteria, _Filter
from .dummy import DummyAssetStore
from ..store.json_file import JsonFileAssetStore
from ..store.base import AssetStoreGroupFacility
from ..services.asset import router

from pathlib import Path

CURRENT_PATH = Path(__file__).parent
ASSETS_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("assets")


class TestAssetGroupFacility(omni.kit.test.AsyncTestCaseFailOnLogError):
    async def setUp(self):
        self._asset_store_group = AssetStoreGroupFacility()
        router.register_facility("asset_store", self._asset_store_group)
        api_version = carb.settings.get_settings_interface().get("exts/artec.services.browser.asset/api_version")
        self._client = AsyncClient(f"local:///{api_version}", app=main.get_app())

    async def tearDown(self):
        await self._client.stop_async()
        self._client = None

    async def test_search_multiple_stores(self):
        self._asset_store_group.clear_stores()
        self._asset_store_group.register_store("DUMMY", DummyAssetStore())
        self._asset_store_group.register_store("NVIDIA", JsonFileAssetStore("NVIDIA", f"{ASSETS_DATA_PATH}/s3.json"))

        res = await self._client.assets.search.post(filter={"categories": ["/Vegetation/Plant_Tropical"]})

        self.assertIn("NVIDIA", res)
        self.assertIn("DUMMY", res)

        self.assertEqual(len(res["NVIDIA"][0]), 17)
        self.assertEqual(len(res["DUMMY"][0]), 0)

    async def test_search_specific_store(self):
        self._asset_store_group.clear_stores()
        self._asset_store_group.register_store("DUMMY", DummyAssetStore())
        self._asset_store_group.register_store("NVIDIA", JsonFileAssetStore("NVIDIA", f"{ASSETS_DATA_PATH}/s3.json"))

        res = await self._client.assets.search.post(
            filter={"categories": ["/Vegetation/Plant_Tropical"]}, vendors=["NVIDIA"]
        )

        self.assertIn("NVIDIA", res)
        self.assertNotIn("DUMMY", res)

        self.assertEqual(len(res["NVIDIA"][0]), 17)

    async def test_page_items(self):
        """ Test that, for a page size of 10, 10 items are returned out of a list of 17
        """
        self._asset_store_group.clear_stores()
        self._asset_store_group.register_store("NVIDIA", JsonFileAssetStore("NVIDIA", f"{ASSETS_DATA_PATH}/s3.json"))

        res = await self._client.assets.search.post(
            filter={"categories": ["/Vegetation/Plant_Tropical"]}, page={"size": 10}
        )

        self.assertEqual(len(res["NVIDIA"][0]), 10)

    async def test_page_items_second_page_larger_size(self):
        """ Test that, for a list of 17 items, if the page size is 10 and the second page is requested 7 items are returned
        """
        self._asset_store_group.clear_stores()
        self._asset_store_group.register_store("NVIDIA", JsonFileAssetStore("NVIDIA", f"{ASSETS_DATA_PATH}/s3.json"))

        res = await self._client.assets.search.post(
            filter={"categories": ["/Vegetation/Plant_Tropical"]}, page={"size": 10, "number": 2}
        )

        self.assertEqual(len(res["NVIDIA"][0]), 7)

    async def test_item_order_by_price_ascending(self):
        """ Test ordering by price of item in ascending order.
        """
        self._asset_store_group.clear_stores()
        self._asset_store_group.register_store("DUMMY", DummyAssetStore())

        res = await self._client.assets.search.post(keywords=["cars"], sort=["price", "asc"])

        retrieved_prices = []
        for item in res["DUMMY"][0]:
            retrieved_prices.append(item["price"])

        self.assertEqual(retrieved_prices, [10.99, 12.99, 13.99, 14.99, 15.99])

    async def test_item_order_by_price_descending(self):
        """ Test ordering by price of item by descending. 
        """
        self._asset_store_group.clear_stores()
        self._asset_store_group.register_store("DUMMY", DummyAssetStore())

        res = await self._client.assets.search.post(keywords=["cars"], sort=["price", "desc"])

        retrieved_prices = []
        for item in res["DUMMY"][0]:
            retrieved_prices.append(item["price"])

        self.assertEqual(retrieved_prices, list(reversed([10.99, 12.99, 13.99, 14.99, 15.99])))


class TestDummyAssetStore(omni.kit.test.AsyncTestCaseFailOnLogError):
    async def test_search_no_criteria(self):
        """Test listing all dummy assets."""
        store = DummyAssetStore()

        (result, *_) = await store.search(search_criteria=SearchCriteria(), search_timeout=60)
        self.assertEqual(len(result), 5)

    async def test_search_category(self):
        store = DummyAssetStore()
        search = SearchCriteria(filter=_Filter(categories=["/vehicles/cars/sedan"]))
        (result, *_) = await store.search(search_criteria=search, search_timeout=60)
        self.assertEqual(len(result), 3)

    async def test_search_order_by_name(self):
        store = DummyAssetStore()
        search = SearchCriteria(keywords=["sedan"], sort=["name", "desc"])

        (result, *_) = await store.search(search_criteria=search, search_timeout=60)
        retrieved_names = []
        for item in result:
            retrieved_names.append(item.name)

        self.assertEqual(retrieved_names, ["car-sedan-3", "car-sedan-2", "car-sedan-1"])


class TestJsonAssetStore(omni.kit.test.AsyncTestCaseFailOnLogError):
    async def test_search_no_criteria(self):
        """Test listing all json assets."""
        store = JsonFileAssetStore("NVIDIA", f"{ASSETS_DATA_PATH}/s3.json")

        (result, *_) = await store.search(search_criteria=SearchCriteria(), search_timeout=60)
        self.assertEqual(len(result), 50)

    async def test_search_category(self):
        store = JsonFileAssetStore("NVIDIA", f"{ASSETS_DATA_PATH}/s3.json")

        search = SearchCriteria(filter=_Filter(categories=["/Vegetation/Plant_Tropical"]))

        (result, *_) = await store.search(search_criteria=search, search_timeout=60)
        self.assertEqual(len(result), 17)
