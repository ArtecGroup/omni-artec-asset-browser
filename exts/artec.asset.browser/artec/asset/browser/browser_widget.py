import asyncio
from typing import Optional, List, Callable
import carb.settings
import carb.dictionary
import omni.kit.app
from omni.kit.browser.core import BrowserSearchBar, BrowserWidget, CategoryItem
from omni import ui

from .search_notification import SearchNotification
from .popup_menu import SortMenu, FilterMenu
from .models import AssetDetailItem
from .style import ICON_PATH


DEFAULT_THUMBNAIL_PADDING = 5
SETTING_ROOT = "/exts/omni.kit.browser.asset_store/"
SETTING_AUTO_SCROLL = SETTING_ROOT + "autoScroll"


class ArtecCloudBrowserWidget(BrowserWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sort_menu = None
        self._filter_menu = None
        self._filter_vendor = None
        self._update_setting = omni.kit.app.SettingChangeSubscription(
            "/exts/omni.kit.browser.asset_store/showCategory", self._on_show_category_changed
        )

        self._load_future = None
        self._more_details = True
        self._thumbnail_sub_id = None

        self._detail_kwargs["delegate"].set_request_more_fn(self._request_more_assets)

        # Get categories from model
        self._load_categories()
        self._browser_model.on_refresh_provider_fn = self._on_refresh_provider
        self._browser_model.on_enable_provider_fn = self._on_enable_provider

    def destroy(self):
        if self._load_future is not None:
            if not self._load_future.done():
                self._load_future.cancel()

        self._update_setting = None
        if self._sort_menu is not None:
            self._sort_menu.destroy()

        if self._thumbnail_sub_id:
            self.remove_thumbnail_size_changed_fn(self._thumbnail_sub_id)

        super().destroy()

    def _build_right_panel(self):
        with ui.ZStack():
            self._build_detail_panel()

        if self._zoom_bar:
            self._zoom_bar.set_on_hovered_fn(self._on_zoombar_hovered)

        auto_scroll = carb.settings.get_settings().get(SETTING_AUTO_SCROLL)
        if auto_scroll:
            self._detail_scrolling_frame.set_scroll_y_changed_fn(self._on_detail_scroll_y_changed)

    def _build_detail_panel(self):
        # Add search bar
        with ui.VStack(spacing=5):
            with ui.HStack(spacing=4, height=26):
                self._search_bar = BrowserSearchBar(options_menu=None, subscribe_edit_changed=False)
                with ui.VStack(width=26):
                    ui.Spacer()
                    self._filter_button = ui.Button(
                        image_width=20,
                        image_height=20,
                        width=26,
                        height=26,
                        name="filter",
                        clicked_fn=self._trigger_filter_menu,
                        style_type_name_override="SearchBar.Button",
                    )
                    ui.Spacer()
                with ui.VStack(width=26):
                    ui.Spacer()
                    self._sort_button = ui.Button(
                        image_width=20,
                        image_height=20,
                        width=26,
                        height=26,
                        name="sort",
                        clicked_fn=self._trigger_sort_menu,
                        style_type_name_override="SearchBar.Button",
                    )
                    ui.Spacer()
            with ui.ZStack():
                super()._build_right_panel()

                def __clear_search():
                    self._search_bar.clear_search()

                self._search_notification = SearchNotification(__clear_search)

        self._search_bar.bind_browser_widget(self)
        self._thumbnail_sub_id = self.add_thumbnail_size_changed_fn(self._on_thumbnail_size_changed)
        self._search_notification.visible = False

    def _build_detail_view_internal(self):
        self._thumbnail_padding = self._get_thumbnail_padding(self._detail_kwargs["thumbnail_size"])
        self._detail_kwargs["thumbnail_padding_width"] = self._thumbnail_padding
        self._detail_kwargs["thumbnail_padding_height"] = self._thumbnail_padding

        super()._build_detail_view_internal()
        self._detail_view.set_extra_filter_fn(self._on_extra_filter)

    def _on_category_selected(self, category_item: Optional[CategoryItem]) -> None:
        if category_item is None:
            # Alway show "ALL" if nothing selected
            self.category_selection = [self._browser_model._category_items[0]]
            return
        if category_item is not None:
            super()._on_category_selected(category_item)

            self._load_assets(category_item, lambda: self._detail_view.model._item_changed(None))
        else:
            super()._on_category_selected(category_item)

    def show_widgets(
        self,
        collection: Optional[bool] = None,
        category: Optional[bool] = None,
        detail: Optional[bool] = None,
        expand_root: Optional[bool] = None,
    ) -> None:
        # Show collection control but disable it and make it transparent
        super().show_widgets(collection=collection, category=category, detail=detail)
        self._collection_combobox.enabled = False

        # if expand_root:
        #    self._category_view.set_expanded(self._category_model.get_item_children()[0], True, False)

    def filter_details(self, filter_words: Optional[List[str]]):
        self._begin_search()
        self._browser_model.search_words = filter_words

        # Clean cache detail items in browser model
        if self.category_selection:
            for category_item in self.category_selection:
                self._browser_model._item_changed(category_item)

        def __show_filter_results():
            self._detail_view.model._item_changed(None)
            self._end_search()

        if self.category_selection:
            self._load_assets(self.category_selection[0], __show_filter_results)
        else:
            # Force to refresh detail view for new filter words
            self._detail_view.model._item_changed(None)

    def _trigger_sort_menu(self) -> None:
        if self._sort_menu is None:
            self._sort_menu = SortMenu(self._on_sort_changed)
        else:
            self._sort_menu.visible = True

        self._sort_menu.position_x = self._sort_button.screen_position_x
        self._sort_menu.position_y = self._sort_button.screen_position_y + self._sort_button.computed_height

    def _on_sort_changed(self, sort_field: str, sort_order: str) -> None:
        self._browser_model.change_sort_args(sort_field, sort_order)
        if self.category_selection:
            self._load_assets(self.category_selection[0], lambda: self._detail_view.model._item_changed(None))

    def _trigger_filter_menu(self) -> None:
        if self._filter_menu is None:
            self._filter_menu = FilterMenu(list(self._browser_model.providers.keys()), self._on_filter_changed)
        else:
            self._filter_menu.visible = True

        self._filter_menu.position_x = self._sort_button.screen_position_x
        self._filter_menu.position_y = self._sort_button.screen_position_y + self._sort_button.computed_height

    def _on_filter_changed(self, filter_vendor: str) -> None:
        self._browser_model.search_provider = None if filter_vendor == "All" else filter_vendor
        if self.category_selection:
            self._load_assets(self.category_selection[0], lambda: self._detail_view.model._item_changed(None))

    def _on_show_category_changed(self, item: carb.dictionary.Item, event_type) -> None:
        # Show and expand category
        if event_type == carb.settings.ChangeEventType.CHANGED:
            url = str(item)
            if url:
                full_chain = []
                category_item = self._find_category_item(url, None, full_chain)
                if category_item:
                    self.category_selection = [category_item]
                    # Expand to show selected category
                    for item in full_chain:
                        self._category_view.set_expanded(item, True, False)

    def _on_refresh_provider(self, provider: str, item: carb.dictionary.Item, event_type) -> None:
        # Refresh category
        if event_type != carb.settings.ChangeEventType.CHANGED:
            return

        async def __refresh_categories_async():
            await omni.kit.app.get_app().next_update_async()
            await self._browser_model.list_categories_async()

            # Refresh categories list
            self._browser_model._item_changed(self.collection_selection)
            self._category_view.model._item_changed(None)

            # Default select "ALL"
            self.category_selection = [self._browser_model._category_items[0]]

        asyncio.ensure_future(__refresh_categories_async())

    def _on_enable_provider(self, provider: str, item: carb.dictionary.Item, event_type) -> None:
        if event_type != carb.settings.ChangeEventType.CHANGED:
            return

        async def __refresh_providers_async():
            await self._browser_model.list_providers_async()
            await self._browser_model.list_categories_async()

            # Refresh provider filter menu
            if self._filter_menu:
                self._filter_menu.refresh(list(self._browser_model.providers.keys()))

            # Refresh categories list
            self._browser_model._item_changed(self.collection_selection)
            await omni.kit.app.get_app().next_update_async()
            self._category_view.model._item_changed(None)

            self._on_category_selected(None)

        asyncio.ensure_future(__refresh_providers_async())

    def _find_category_item(
        self, url: str, category_item: Optional[CategoryItem] = None, full_chain: Optional[List[CategoryItem]] = None
    ) -> Optional[CategoryItem]:
        if category_item is None:
            # Find in root
            for child in self._category_model.get_item_children():
                found_item = self._find_category_item(url, child, full_chain)
                if found_item:
                    return found_item
            else:
                return None
        else:
            if category_item.url == url:
                return category_item
            else:
                if full_chain is not None:
                    full_chain.append(category_item)
                for child in category_item.children:
                    # Find in children
                    found_item = self._find_category_item(url, child, full_chain)
                    if found_item is not None:
                        return found_item
                else:
                    if full_chain is not None:
                        full_chain.pop()
                    return None

    def _on_extra_filter(self, item: AssetDetailItem) -> bool:
        if self._filter_vendor is None:
            return True
        else:
            if isinstance(item, AssetDetailItem):
                return item.asset_model["vendor"] == self._filter_vendor
            else:
                return True

    def _load_assets(
        self, category_item: CategoryItem, callback: Callable[[None], None] = None, reset: bool = True
    ) -> None:
        if reset:
            self._begin_search()

            self._browser_model.reset_assets()
            self._detail_view.model._item_changed(None)
        else:
            self._detail_kwargs["delegate"].more_item_image.source_url = f"{ICON_PATH}/search.png"
            self._detail_kwargs["delegate"].more_item_label.text = "Searching..."
            self._detail_kwargs["delegate"].more_item_center_tips.text = "Searching..."
            self._detail_kwargs["delegate"].more_item_right_tips.text = ""

        if self._load_future is not None:
            if not self._load_future.done():
                self._load_future.cancel()
        if reset:
            self._more_details = True

        def __assets_loaded():
            self._detail_view.model._item_changed(None)
            self._end_search()

        self._load_future = asyncio.ensure_future(self._load_asset_async(category_item, __assets_loaded, reset=reset))

    async def _load_asset_async(
        self, category_item: CategoryItem, callback: Callable[[None], None] = None, reset: bool = True
    ):
        self._more_details = await self._browser_model.list_assets_async(category_item, callback, reset=reset)
        self._end_search()

    def _on_thumbnail_size_changed(self, thumbnail_size: int) -> None:
        self._detail_kwargs["delegate"].on_thumbnail_size_changed(thumbnail_size)
        thumbnail_padding = self._get_thumbnail_padding(thumbnail_size)
        if thumbnail_padding != self._thumbnail_padding:
            self._thumbnail_padding = thumbnail_padding
            self._detail_view.thumbnail_padding_height = thumbnail_padding
            self._detail_view.thumbnail_padding_width = thumbnail_padding

    def _load_categories(self):
        async def __load_categories_async():
            await self._browser_model.list_categories_async()

            # Show categories list
            self.collection_index = 0

            self.category_selection = [self._browser_model._category_items[0]]

        asyncio.ensure_future(__load_categories_async())

    def _request_more_assets(self):
        # Require more assets
        if self.category_selection:
            self._load_assets(
                self.category_selection[0], lambda: self._detail_view.model._item_changed(None), reset=False
            )

    def _on_zoombar_hovered(self, hovered: bool) -> None:
        # When zoombar hovered, disable hover window.
        # Otherwise zoombar will lost focus and cannot change thumbnail size anymore.
        self._detail_kwargs["delegate"].enable_hovered(not hovered)

    def _get_thumbnail_padding(self, thumbnail_size):
        if thumbnail_size > 384:
            return 3 * DEFAULT_THUMBNAIL_PADDING
        elif thumbnail_size > 192:
            return 2 * DEFAULT_THUMBNAIL_PADDING
        else:
            return DEFAULT_THUMBNAIL_PADDING

    def _begin_search(self) -> None:
        self._search_notification.set_message("Searching...", show_clear=False)
        self._search_notification.visible = True

    def _end_search(self) -> None:
        if len(self._browser_model._assets) == 0:
            if self._browser_model.search_words is not None:
                message = " ".join(self._browser_model.search_words)
                message = f'"{message}" not found'
                self._search_notification.set_message(message)
                self._search_notification.visible = True
            else:
                if self._browser_model.search_provider:
                    message = f"No asset found ({self._browser_model.search_provider} only)!"
                else:
                    message = "No assets found!"
                self._search_notification.set_message(message, show_clear=False)
                self._search_notification.visible = True
        else:
            self._search_notification.visible = False

    def _on_detail_scroll_y_changed(self, y: float) -> None:
        try:
            if self._more_details and y >= self._detail_scrolling_frame.scroll_y_max and self.category_selection:
                # Require more assets
                self._request_more_assets()

        except AttributeError:
            # scroll_y_max required new kit
            # carb.log_error("Update kit to enable scrolling event!")
            pass
