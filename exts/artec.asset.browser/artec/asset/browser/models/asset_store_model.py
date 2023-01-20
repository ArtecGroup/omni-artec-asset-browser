import asyncio
import copy
import carb
import carb.dictionary
import carb.settings
import omni.usd
import omni.kit.app
import omni.client

from omni.kit.browser.core import AbstractBrowserModel, CollectionItem, CategoryItem, DetailItem
from typing import Dict, List, Optional, Union, Callable
from omni.services.browser.asset import AssetModel, ProviderModel, BaseAssetStore
from omni.services.browser.asset import get_instance as get_asset_services
from pxr import Tf

from .asset_store_client import AssetStoreClient
from .asset_detail_item import AssetDetailItem, MoreDetailItem, SearchingDetailItem
from .main_navigation_item import MainNavigationItem
from .common_categories import COMMON_CATEGORIES

SETTING_ROOT = "/exts/omni.kit.browser.asset_store/"
SETTING_PROVIDER_ROOT = SETTING_ROOT + "provider"
SETTING_PAGE_SIZE = SETTING_ROOT + "pageSize"
SETTING_SINGLE_PROVIDER = SETTING_ROOT + "singleProvider"
CATEGORY_ANY = "All"


class AssetStoreModel(AbstractBrowserModel):
    """
    Represents the browser model for asset store services.
    """

    def __init__(self):
        super().__init__(always_realod_detail_items=True)

        # Dummy collection item. Not displayed, but required for browser model
        self._collection_item = CollectionItem("store", "")

        # For browser UI, category items in category treeview
        self._category_items: List[MainNavigationItem] = []

        # Category url <=> Category item
        self._cached_catetory_items: Dict[str, MainNavigationItem] = {}

        # Category item <=> Detail items of this category item (without children category item)
        self._cached_detail_items: Dict[MainNavigationItem, List[DetailItem]] = {}

        # Store
        store_url = carb.settings.get_settings().get(SETTING_PROVIDER_ROOT)
        self._store_client = AssetStoreClient(store_url)

        # Sort of detail items, default by name with ascending
        self._sort_args = {"key": lambda item: item["name"], "reverse": False}

        self.search_words: Optional[List[str]] = None
        self.search_provider: Optional[str] = None
        self._search_sort_args = ["name", "asc"]

        # Searched asset models
        self._assets: Optional[List[AssetModel]] = None
        self._categories: Optional[Dict] = None
        self.providers: Dict[str, ProviderModel] = {}
        self._refresh_provider_sub: Dict[str, omni.kit.app.SettingChangeSubscription] = {}
        self._enable_provider_sub: Dict[str, omni.kit.app.SettingChangeSubscription] = {}
        self.on_refresh_provider_fn: Callable[[str], None] = None
        self.on_enable_provider_fn: Callable[[str], None] = None
        self._page_number = 1
        self._more_assets = False
        self._searching = False

        asyncio.ensure_future(self.list_providers_async())

    def destroy(self):
        for provider in self._refresh_provider_sub:
            self._refresh_provider_sub[provider] = None
        for provider in self._refresh_provider_sub:
            self._refresh_provider_sub[provider] = None
        self._store_client.destroy()

    def get_store(self, vendor: str) -> BaseAssetStore:
        asset_services = get_asset_services()
        if asset_services:
            return asset_services.get_store(vendor)
        return None

    def get_collection_items(self) -> List[CollectionItem]:
        """Override to get list of collection items"""
        return [self._collection_item]

    def get_category_items(self, item: CollectionItem) -> List[CategoryItem]:
        """Override to get list of category items"""
        self._category_items = []
        self._cached_catetory_items = {}

        # Public categories
        full_categories = copy.deepcopy(COMMON_CATEGORIES)
        for provider, categories in self._categories.items():
            if provider in self.providers:
                if self.providers[provider]["private"]:
                    continue

            for name in categories:
                if name in full_categories:
                    full_categories[name].extend(categories[name])
                    full_categories[name] = list(set(full_categories[name]))
                else:
                    full_categories[name] = categories[name]

        def __create_provider_category_items(category_list, provider=None, root=None):

            for name in category_list:
                self._create_category_chain(name, provider, root=root)
                if category_list[name]:
                    category_list[name].sort()
                    for sub in category_list[name]:
                        url = name + "/" + sub
                        # Create category item
                        self._create_category_chain(url, provider, root=root)

        __create_provider_category_items(full_categories)

        self._category_items.sort(key=lambda item: item.name)

        # Private categories
        for provider, categories in self._categories.items():
            if provider in self.providers:
                if self.providers[provider]["private"]:
                    root_category_item = self._create_category_item(provider, None, provider)
                    if self.providers[provider]["configurable"]:
                        root_category_item.configurable = True
                    self._category_items.insert(0, root_category_item)
                    __create_provider_category_items(categories, provider=provider, root=root_category_item)

        # All
        self._category_items.insert(0, self._create_category_item(CATEGORY_ANY, None, list(self.providers.keys())))

        return self._category_items

    def get_detail_items(self, item: CategoryItem) -> List[DetailItem]:
        """Override to get list of detail items"""
        detail_items = []

        if self._assets:
            for asset in self._assets:
                detail_items.append(self._create_detail_item(asset))

        if self._more_assets:
            detail_items.append(MoreDetailItem())

        if self._searching:
            detail_items.append(SearchingDetailItem())

        return detail_items

    def execute(self, item: Union[AssetDetailItem, CategoryItem]) -> None:
        if isinstance(item, CategoryItem):
            # TODO: Jump to selected category item in category tree view
            pass
        elif isinstance(item, AssetDetailItem):
            # Create a Reference of the Props in the stage
            stage = omni.usd.get_context().get_stage()
            if not stage:
                return

            name = item.name_model.as_string.split(".")[0]

            prim_path = omni.usd.get_stage_next_free_path(stage, "/" + Tf.MakeValidIdentifier(name), True)

            omni.kit.commands.execute(
                "CreateReferenceCommand", path_to=prim_path, asset_path=item.url, usd_context=omni.usd.get_context()
            )

    def change_sort_args(self, sort_field: str, sort_order: str) -> None:
        """Change sort args with new field and order"""
        sort_key = "name"
        if sort_field == "Date":
            sort_key = "published_at"
        elif sort_field == "Category":
            sort_key = "category"
        elif sort_field == "Price":
            sort_key = "price"

        self._search_sort_args = [sort_key]

        if sort_order == "Descending":
            self._search_sort_args.append("desc")
        else:
            self._search_sort_args.append("asc")

        if sort_field == "Date":
            sort_fn = lambda item: item["published_at"]
        elif sort_field == "Category":
            sort_fn = lambda item: item["category"]
        elif sort_field == "Vendor":
            sort_fn = lambda item: item["vendor"]
        elif sort_field == "Price":
            sort_fn = lambda item: item["price"]
        else:
            # Default, always sort by name
            sort_fn = lambda item: item["name"]
        self._sort_args = {"key": sort_fn, "reverse": sort_order == "Descending"}

    def get_sort_args(self) -> Dict:
        """
        Get sort args to sort detail items. 
        """
        return self._sort_args

    def config_provider(self, provider: str) -> None:
        asyncio.ensure_future(self._store_client.config_provider_async(provider))

    def _on_client_prepared(self, client: AssetStoreClient) -> None:
        # Client prepared, notify to model updated and regenerate items
        self._category_items = []
        self._cached_catetory_items = {}
        self._cached_detail_items = {}

        self._item_changed(self._collection_item)

    def _create_category_chain(
        self, category_url: str, provider_name: Optional[str], root: MainNavigationItem = None
    ) -> MainNavigationItem:
        """Create catetory chain by url."""
        if category_url in self._cached_catetory_items:
            category_item = self._cached_catetory_items[category_url]
            if provider_name:
                category_item.add_provider(provider_name)
            return category_item

        pos = category_url.rfind("/")
        # Create new category item
        category_item = self._create_category_item(category_url[pos + 1 :], category_url, provider_name)
        if pos < 0:
            # Root category
            if root:
                root.children.append(category_item)
            else:
                self._category_items.append(category_item)
        elif pos >= 0:
            parent_category_item = self._create_category_chain(category_url[:pos], provider_name, root=root)
            parent_category_item.children.append(category_item)

        return category_item

    def _create_category_item(
        self, category_name: str, category_url: Optional[str], provider_name: str
    ) -> MainNavigationItem:
        category_item = MainNavigationItem(category_name, category_url, provider_name)

        self._cached_catetory_items[category_url] = category_item

        return category_item

    def _create_detail_item(self, asset_model: AssetModel) -> DetailItem:
        return AssetDetailItem(asset_model)

    def reset_assets(self):
        self._assets = []
        self._page_number = 1
        self._more_assets = False

    async def list_assets_async(
        self, category_item: MainNavigationItem, callback: Callable[[None], None] = None, reset: bool = True
    ) -> bool:
        if reset:
            self.reset_assets()

        self._more_assets = False

        page_size = carb.settings.get_settings().get(SETTING_PAGE_SIZE)
        single_provider = carb.settings.get_settings().get(SETTING_SINGLE_PROVIDER)

        if category_item.providers:
            # If category is private, alwasy search for matched provider but do not care provider filter
            if self.search_provider:
                if self.search_provider not in category_item.providers:
                    carb.log_warn(
                        f"'{category_item.name}' used for {category_item.providers} only, ignore filter '{self.search_provider}'!"
                    )
                    providers = category_item.providers
                else:
                    providers = [self.search_provider]
            else:
                providers = category_item.providers
        elif self.search_provider:
            providers = [self.search_provider]
        else:
            providers = list(self.providers.keys())

        if single_provider:
            self._searching = True
            queries: Dict[str, asyncio.Future] = {}
            for provider in providers:
                queries[provider] = asyncio.ensure_future(
                    self._list_assets_by_vendor_async(
                        category_item.url, page_size, [provider], callback, single_step=True
                    )
                )

            await asyncio.gather(*queries.values(), return_exceptions=True)

            for provider, query in queries.items():
                try:
                    if query.result():
                        self._more_assets = True
                except Exception as exc:
                    carb.log_info(f"Failed to fetch results for {provider}: {type(exc)}, {str(exc)}")

            self._searching = False
            if callback:
                callback()
        else:
            self._more_assets = await self._list_assets_by_vendor_async(
                category_item.url, page_size, providers, callback
            )

        self._page_number += 1
        return self._more_assets

    async def _list_assets_by_vendor_async(self, category_url, page_size, providers, callback, single_step=False):
        carb.log_info(
            f"Searching providers: {providers} with category: {category_url}, keywords: {self.search_words}, page: {self._page_number}"
        )

        (assets, more_assets) = await self._store_client._list_async(
            category_url,
            search_words=self.search_words,
            sort=self._search_sort_args,
            page_size=page_size,
            page_number=self._page_number,
            providers=providers,
        )
        if assets:
            # Filter duplicated results (happended in sketchfab)
            filter_assets = []
            [
                filter_assets.append(asset)
                for asset in assets
                if not asset in filter_assets and not asset in self._assets
            ]

            # Sort new results
            filter_assets.sort(**self._sort_args)
            self._assets.extend(filter_assets)

            carb.log_info(f"  {len(assets)} returned, {len(filter_assets)} valid, total {len(self._assets)}")

            if not single_step and more_assets:
                self._more_assets = True

            if callback:
                callback()
        elif not single_step:
            if callback:
                callback()

        return more_assets

    async def list_categories_async(self):
        self._categories = await self._store_client.list_categories_async()

    async def list_providers_async(self):
        self.providers = await self._store_client.list_providers_async()
        for provider, setting in self.providers.items():
            if provider in self._refresh_provider_sub:
                self._refresh_provider_sub[provider] = None
            if provider in self._enable_provider_sub:
                self._enable_provider_sub[provider] = None
            if setting["refresh_setting"]:
                self._refresh_provider_sub[provider] = omni.kit.app.SettingChangeSubscription(
                    setting["refresh_setting"],
                    lambda item, event_type, p=provider: self._on_refresh_provider(p, item, event_type),
                )
            if setting["enable_setting"]:
                self._enable_provider_sub[provider] = omni.kit.app.SettingChangeSubscription(
                    setting["enable_setting"],
                    lambda item, event_type, p=provider: self._on_enable_provider(p, item, event_type),
                )

    def _on_refresh_provider(self, provider: str, item: carb.dictionary.Item, event_type) -> None:
        if self.on_refresh_provider_fn:
            self.on_refresh_provider_fn(provider, item, event_type)

    def _on_enable_provider(self, provider: str, item: carb.dictionary.Item, event_type) -> None:
        if self.on_enable_provider_fn:
            self.on_enable_provider_fn(provider, item, event_type)

    async def authenticate_async(self, vendor: str, username: str, password: str, callback: Callable[[], None] = None):
        asset_store = self.get_store(vendor)
        if not asset_store:
            return False
        await asset_store.authenticate(username, password)
        if callback:
            callback()

    async def download_async(
        self,
        asset: Dict,
        dest_url: str,
        callback: Callable[[Dict], None] = None,
        on_progress_fn: Callable[[float], None] = None,
    ):
        asset_store = self.get_store(asset.get("vendor"))
        if not asset_store:
            return

        asset_model = AssetModel(
            identifier=asset.get("identifier", ""),
            name=asset.get("name", ""),
            version=asset.get("version", ""),
            published_at=asset.get("publishedAt", ""),
            categories=asset.get("categories", []),
            tags=asset.get("tags", []),
            vendor=asset.get("vendor", ""),
            download_url=asset.get("download_url", ""),
            product_url=asset.get("product_url", ""),
            price=asset.get("price", 0.0),
            thumbnail=asset.get("thumbnail", ""),
        )
        results = await asset_store.download(asset_model, dest_url, on_progress_fn=on_progress_fn, timeout=600)
        if results.get("status") != omni.client.Result.OK:
            carb.log_info(f"Failed to download asset from {asset.get('vendor')}.")
        if callback:
            callback(results)
