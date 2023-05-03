# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from AssetStore class AssetDetailDelegate

import carb
import carb.settings
import omni.ui as ui
import omni.client
import omni.kit.app
from omni.kit.browser.core import DetailDelegate, DetailItem, create_drop_helper
from omni.kit.window.filepicker import FilePickerDialog
from .models import AssetStoreModel, AssetDetailItem, AssetType, MoreDetailItem, SearchingDetailItem
from .hover_window import HoverWindow
from .auth_dialog import AuthDialog
from .download_progress_bar import DownloadProgressBar
from .download_helper import DownloadHelper
from .style import ICON_PATH

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Tuple, Callable
from functools import partial
import webbrowser

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.joinpath("icons")

SETTING_HOVER_WINDOW = "/exts/artec.asset.browser/hoverWindow"
SETTING_MY_ASSET_FOLDERS = "/persistent/exts/omni.kit.browser.asset_provider.local/folders"
SETTING_MY_ASSET_FOLDER_CHANGED = "/exts/omni.kit.browser.asset_provider.local/folderChanged"

MIN_THUMBNAIL_SIZE_HOVER_WINDOW = 192

LABEL_HEIGHT = 32
ASSET_PROVIDER_ICON_SIZE = 32


class AssetDetailDelegate(DetailDelegate):
    """
    Delegate to show asset item in detail view
    Args:
        model (AssetBrowserModel): Asset browser model
    """

    def __init__(self, model: AssetStoreModel):
        super().__init__(model=model)

        self._dragging_url = None
        self._settings = carb.settings.get_settings()
        self._context_menu: Optional[ui.Menu] = None
        self._action_item: Optional[AssetDetailItem] = None
        self._vendor_container: Dict[AssetDetailItem, ui.ZStack] = {}
        self._hover_center_container: Dict[AssetDetailItem, ui.VStack] = {}
        self._hover_center_label: Dict[AssetDetailItem, ui.Label] = {}
        self._hover_container: Dict[AssetDetailItem, ui.VStack] = {}
        self._hover_label: Dict[AssetDetailItem, ui.Label] = {}
        self._hover_background: Dict[AssetDetailItem, ui.Widget] = {}
        self._asset_type_container: Dict[AssetDetailItem, ui.Widget] = {}
        self._asset_type_image: Dict[AssetDetailItem, ui.Image] = {}
        self._download_progress_bar: Dict[AssetDetailItem, DownloadProgressBar] = {}
        self._draggable_urls: Dict[str, str] = {}
        self._auth_dialog: Optional[AuthDialog] = None
        self._pick_folder_dialog: Optional[FilePickerDialog] = None
        self._on_request_more_fn: Callable[[None], None] = None
        self.more_item_image: Optional[ui.Image] = None
        self.more_item_label: Optional[ui.Label] = None
        self.more_item_center_tips: Optional[ui.Label] = None
        self.more_item_right_tips: Optional[ui.Label] = None

        self._enable_hovered = True
        self._asset_type_image_multiple = self._get_asset_type_image_multiple(self.thumbnail_size)

        self._show_hover_window = carb.settings.get_settings().get(SETTING_HOVER_WINDOW)
        if self._show_hover_window:
            self._hover_window = HoverWindow()
        else:
            self._hover_window = None

        self._instanceable_categories = self._settings.get("/exts/omni.kit.browser.asset/instanceable")
        if self._instanceable_categories:
            self._drop_helper = create_drop_helper(
                pickable=True,
                add_outline=True,
                on_drop_accepted_fn=self._on_drop_accepted,
                on_drop_fn=self._on_drop,
            )

        self._download_helper = DownloadHelper()

    def destroy(self):
        self._drop_helper = None
        if self._pick_folder_dialog is not None:
            self._pick_folder_dialog.destroy()
            self._pick_folder_dialog = None

        if self._hover_window:
            self._hover_window.visible = False
            self._hover_window = None

        for item in self._download_progress_bar:
            self._download_progress_bar[item].destroy()

        super().destroy()

    def set_request_more_fn(self, request_more_fn: Callable[[None], None]) -> None:
        self._on_request_more_fn = request_more_fn

    def enable_hovered(self, enable: bool) -> None:
        self._enable_hovered = enable

    def get_thumbnail(self, item) -> str:
        """Set default sky thumbnail if thumbnail is None"""
        if item.thumbnail is None:
            return f"{ICON_PATH}/usd_stage_256.png"
        else:
            return item.thumbnail

    def get_label_height(self) -> int:
        # return 0 if self.hide_label else two lines for small thumbnail size and one line for large thumbnail size
        return LABEL_HEIGHT

    def on_drag(self, item: AssetDetailItem) -> str:
        """Could be dragged to viewport window"""
        if item.asset_type != AssetType.NORMAL:
            # Cannot drag if item to be downloaded or external link
            return ""

        thumbnail = self.get_thumbnail(item)
        icon_size = 128
        with ui.VStack(width=icon_size):
            if thumbnail:
                ui.Spacer(height=2)
                with ui.HStack():
                    ui.Spacer()
                    ui.ImageWithProvider(thumbnail, width=icon_size, height=icon_size)
                    ui.Spacer()
            ui.Label(
                item.name,
                word_wrap=False,
                elided_text=True,
                skip_draw_when_clipped=True,
                alignment=ui.Alignment.TOP,
                style_type_name_override="GridView.Item",
            )

        self._dragging_url = None
        if self._instanceable_categories:
            # For required categories, need to set instanceable after dropped
            url = item.url
            pos = url.rfind("/")
            if pos > 0:
                url = url[:pos]
            for category in self._instanceable_categories:
                if category in url:
                    self._dragging_url = item.url
                    break
        return item.url

    def _on_drop_accepted(self, url):
        # Only hanlder dragging from asset browser
        return url == self._dragging_url

    def _on_drop(self, url, target, viewport_name, context_name):
        saved_instanceable = self._settings.get("/persistent/app/stage/instanceableOnCreatingReference")
        if not saved_instanceable and url == self._dragging_url:
            # Enable instanceable for viewport asset drop handler
            self._settings.set_bool("/persistent/app/stage/instanceableOnCreatingReference", True)

            async def __restore_instanceable_flag():
                # Waiting for viewport asset dropper handler completed
                await omni.kit.app.get_app().next_update_async()
                self._settings.set("/persistent/app/stage/instanceableOnCreatingReference", saved_instanceable)

            asyncio.ensure_future(__restore_instanceable_flag())

        self._dragging_url = None
        # Let viewport do asset dropping
        return None

    def _single_item_changed(self, item: AssetDetailItem):
        if self._cached_label_widgets[item] is not None:
            label_height = self._cached_label_widgets[item].computed_height
        super()._single_item_changed(item)
        if self._cached_label_widgets[item] is not None:
            self._cached_label_widgets[item].height = ui.Pixel(label_height)

    def on_double_click(self, item: AssetDetailItem) -> None:
        if isinstance(item, AssetDetailItem):
            if item.asset_type == AssetType.EXTERNAL_LINK or item.asset_type == AssetType.DOWNLOAD:
                webbrowser.open(item.asset_model["product_url"])
            elif item.asset_type == AssetType.NORMAL:
                return super().on_double_click(item)
        else:
            if self._on_request_more_fn:
                self._on_request_more_fn()

    def on_right_click(self, item: DetailItem) -> None:
        """Show context menu"""
        self._action_item = item
        if isinstance(item, AssetDetailItem):
            show_web = item.asset_model.get("product_url", "") != ""
            show_collect = False
            try:
                import omni.kit.tool.collect
                show_collect = True
            except ImportError:
                carb.log_warn("Please enable omni.kit.tool.collect first to collect.")

            if show_web or show_collect:
                self._context_menu = ui.Menu("Asset browser context menu")
                with self._context_menu:
                    # TODO: Comment-out Download context-menu option
                    # with ui.Menu("Download"):
                    #     if item.asset_model.get("fusions"):
                    #         for fusion in item.asset_model.get("fusions"):
                    #             ui.MenuItem(
                    #                 fusion["name"], triggered_fn=partial(webbrowser.open, fusion["download_url"])
                    #             )
                    #             ui.Line(alignment=ui.Alignment.BOTTOM, style_type_name_override="MenuSeparator")
                    #             ui.Separator()

                    if show_web:
                        ui.MenuItem(
                            "Open in Web Browser",
                            triggered_fn=partial(webbrowser.open, item.asset_model["product_url"]),
                        )
                    if show_collect:
                        ui.MenuItem("Collect", triggered_fn=self._collect)
                self._context_menu.show()

    def build_thumbnail(self, item: AssetDetailItem, container: ui.Widget = None) -> Optional[ui.Image]:
        if not container:
            container = ui.ZStack()

        if hasattr(item, "uid"):
            if item.uid in self._draggable_urls:
                item.url = self._draggable_urls[item.uid]
                item.asset_type = AssetType.NORMAL

        with container:
            thumbnail = self.get_thumbnail(item)
            image = ui.Image(
                thumbnail or "",
                fill_policy=ui.FillPolicy.PRESERVE_ASPECT_FIT
                if isinstance(item, SearchingDetailItem)
                else ui.FillPolicy.PRESERVE_ASPECT_CROP,
                style_type_name_override="GridView.Image",
            )
            if isinstance(item, MoreDetailItem):
                self.more_item_image = image

            # Vendor image
            self._build_vendor_image(item)

            # Asset type background and image
            self._asset_type_container[item] = ui.VStack()
            self._build_asset_type(item)

            # For displaying download progress over the thumbnail
            self._download_progress_bar[item] = DownloadProgressBar()

            # Selection rectangle
            ui.Rectangle(style_type_name_override="GridView.Item.Selection")

        return image

    def on_hover(self, item: DetailItem, hovered: bool) -> None:
        if not self._enable_hovered:
            return

        if self.thumbnail_size < MIN_THUMBNAIL_SIZE_HOVER_WINDOW:
            if self._show_hover_window:
                image_size = self.thumbnail_size * 1.15
                offset = self.thumbnail_size * 0.15 / 2
                window_position_x = self._cached_thumbnail_widgets[item].screen_position_x - offset
                window_position_y = self._cached_thumbnail_widgets[item].screen_position_y - offset
                self._hover_window.show(item, image_size, LABEL_HEIGHT, window_position_x, window_position_y)
            else:
                if item in self._hover_center_container:
                    self._hover_center_container[item].visible = hovered
        else:
            if item in self._hover_container:
                self._hover_container[item].visible = hovered
                self._hover_background[item].visible = hovered

    def on_thumbnail_size_changed(self, thumbnail_size: int) -> None:
        new_multiple = self._get_asset_type_image_multiple(thumbnail_size)
        if new_multiple != self._asset_type_image_multiple:
            self._asset_type_image_multiple = new_multiple
            for item in self._asset_type_container:
                self._build_asset_type(item)
            for item in self._vendor_container:
                self._vendor_container[item].width = ui.Pixel(
                    ASSET_PROVIDER_ICON_SIZE * self._asset_type_image_multiple
                )
                self._vendor_container[item].height = ui.Pixel(
                    ASSET_PROVIDER_ICON_SIZE * self._asset_type_image_multiple
                )

    def _build_label(self, item: AssetDetailItem, container: ui.Widget = None) -> ui.Widget:
        """
        Display label per detail item
        Args:
            item (AssetDetailItem): detail item to display
        """
        if not container:
            container = ui.ZStack(height=LABEL_HEIGHT)

        with container:
            ui.Rectangle(height=0, style_type_name_override="GridView.Item.Frame")
            with ui.ZStack():
                # TODO: fix hover
                self._hover_background[item] = ui.Rectangle(
                    visible=False, style_type_name_override="GridView.Item.Hover.Background"
                )
                with ui.HStack(height=LABEL_HEIGHT):
                    label = self._build_name_and_owner(item)
                    self._build_tips_at_right(item)
                if not self._show_hover_window:
                    self._build_tips_at_center(item)

        return label

    def _build_tips_at_right(self, item: AssetDetailItem) -> None:
        self._hover_container[item] = ui.ZStack(width=0, visible=False)
        with self._hover_container[item]:
            self._hover_label[item] = ui.Label(
                item.tips,
                name=item.asset_type,
                width=0,
                alignment=ui.Alignment.RIGHT,
                style_type_name_override="GridView.Item.Tips.Text",
            )
            if isinstance(item, MoreDetailItem):
                self.more_item_right_tips = self._hover_label[item]

    def _build_tips_at_center(self, item: AssetDetailItem) -> None:
        # Hover background and text
        self._hover_center_container[item] = ui.ZStack(visible=False)
        with self._hover_center_container[item]:
            ui.Rectangle(style_type_name_override="GridView.Item.Hover.Background")
            self._hover_center_label[item] = ui.Label(
                # TODO: use download link in tips ?
                item.tips,
                name=item.asset_type,
                alignment=ui.Alignment.CENTER,
                style_type_name_override="GridView.Item.Tips.Text",
            )
            if isinstance(item, MoreDetailItem):
                self.more_item_center_tips = self._hover_center_label[item]

    def _build_name_and_owner(self, item: AssetDetailItem) -> ui.Label:
        text = self.get_label(item)

        with ui.VStack(height=LABEL_HEIGHT):
            label = ui.Label(
                text or "",
                word_wrap=True,
                elided_text=True,
                skip_draw_when_clipped=True,
                alignment=ui.Alignment.LEFT,
                style_type_name_override="GridView.Item",
            )
            if isinstance(item, AssetDetailItem):
                with ui.HStack():
                    ui.Label(
                        "by " + item.asset_model["user"],
                        elided_text=True,
                        style_type_name_override="GridView.Item.User",
                    )
                    ui.Spacer()
            else:
                ui.Label("")
                self.more_item_label = label

        return label

    def _build_vendor_image(self, item: AssetDetailItem):
        vendor_image = self._get_vendor_image(item)
        if not vendor_image:
            return
        self._vendor_container[item] = ui.Image(
            vendor_image,
            width=ASSET_PROVIDER_ICON_SIZE,
            height=ASSET_PROVIDER_ICON_SIZE,
            fill_policy=ui.FillPolicy.STRETCH,
            style_type_name_override="GridView.Item.Vendor.Image",
        )

    def _build_asset_type(self, item: AssetDetailItem):
        (type_image_url, type_image_size) = self._get_asset_type_image(item)
        tips_size = 32 * self._asset_type_image_multiple
        type_image_size *= self._asset_type_image_multiple
        self._asset_type_container[item].clear()
        with self._asset_type_container[item]:
            ui.Spacer()
            with ui.HStack(height=tips_size):
                ui.Spacer()
                with ui.ZStack(width=tips_size):
                    ui.Triangle(
                        alignment=ui.Alignment.RIGHT_TOP, style_type_name_override="GridView.Item.Tips.Background"
                    )
                    with ui.VStack():
                        ui.Spacer()
                        with ui.HStack(height=0):
                            ui.Spacer()
                            self._asset_type_image[item] = ui.Image(
                                type_image_url,
                                width=type_image_size,
                                height=type_image_size,
                                fill_policy=ui.FillPolicy.STRETCH,
                                mouse_pressed_fn=lambda x, y, btn, flag, item=item: self._on_type_image_pressed(item),
                                style_type_name_override="GridView.Item.Tips.Image",
                            )

    def _get_asset_type_image(self, item: AssetDetailItem) -> Tuple[str, int]:
        """Get item tips image url and text"""
        if isinstance(item, AssetDetailItem):
            if item.asset_type == AssetType.EXTERNAL_LINK:
                return (f"{ICON_PATH}/External_link_green.svg", 16)
            elif item.asset_type == AssetType.DOWNLOAD:
                return (f"{ICON_PATH}/Download_dark.svg", 20)
            elif item.asset_type == AssetType.NORMAL:
                return (f"{ICON_PATH}/finger_drag_dark.svg", 24)
            else:
                return ("", 0)
        else:
            return ("", 0)

    def _get_vendor_image(self, item: AssetDetailItem) -> str:
        """Get item vendor image url"""
        if isinstance(item, AssetDetailItem):
            vendor_name = item.asset_model["vendor"]
            return self._model.providers[vendor_name]["icon"]
        else:
            return ""

    def _collect(self):
        try:
            import omni.kit.tool.collect

            collect_instance = omni.kit.tool.collect.get_instance()
            collect_instance.collect(self._action_item.url)
            collect_instance = None
        except ImportError:
            carb.log_warn("Failed to import collect module (omni.kit.tool.collect). Please enable it first.")
        except AttributeError:
            carb.log_warn("Require omni.kit.tool.collect v2.0.5 or later!")

    def _download_asset(self, item: AssetDetailItem) -> None:
        """Download asset"""

        def on_authenticate(item: AssetDetailItem, dialog: AuthDialog):
            def check_authorized(item: AssetDetailItem, dialog: AuthDialog):
                if item.authorized():
                    dialog.hide()
                    self.select_download_folder(item)
                else:
                    dialog.warn_password()

            asyncio.ensure_future(
                self._model.authenticate_async(
                    item.asset_model["vendor"], dialog.username, dialog.password, lambda: check_authorized(item, dialog)
                )
            )

        def on_cancel(item: AssetDetailItem, dialog: AuthDialog):
            dialog.hide()
            if item and "product_url" in item.asset_model:
                webbrowser.open(item.asset_model["product_url"])

        if item.asset_type != AssetType.DOWNLOAD:
            return
        elif item.authorized():
            self.select_download_folder(item)
        else:
            if not self._auth_dialog:
                self._auth_dialog = AuthDialog()
            self._auth_dialog.show(
                item.asset_model["vendor"],
                click_okay_handler=partial(on_authenticate, item),
                click_cancel_handler=partial(on_cancel, item),
            )

    def select_download_folder(self, item: AssetDetailItem):
        self._action_item = item
        if self._pick_folder_dialog is None:
            self._pick_folder_dialog = self._create_filepicker(
                "Select Directory to Download Asset", click_apply_fn=self._on_folder_picked, dir_only=True
            )
        self._pick_folder_dialog.show()

    def _create_filepicker(
        self,
        title: str,
        filters: list = ["All Files (*)"],
        click_apply_fn: Callable = None,
        error_fn: Callable = None,
        dir_only: bool = False,
    ) -> FilePickerDialog:
        async def on_click_handler(
            filename: str, dirname: str, dialog: FilePickerDialog, click_fn: Callable, dir_only: bool
        ):
            fullpath = None
            if dir_only:
                fullpath = dirname
            else:
                if dirname:
                    fullpath = f"{dirname}/{filename}"
                elif filename:
                    fullpath = filename
            if click_fn:
                click_fn(fullpath)
            dialog.hide()

        dialog = FilePickerDialog(
            title,
            allow_multi_selection=False,
            apply_button_label="Select",
            click_apply_handler=lambda filename, dirname: asyncio.ensure_future(
                on_click_handler(filename, dirname, dialog, click_apply_fn, dir_only)
            ),
            click_cancel_handler=lambda filename, dirname: dialog.hide(),
            item_filter_options=filters,
            error_handler=error_fn,
        )
        dialog.hide()
        return dialog

    def _on_folder_picked(self, url: Optional[str]) -> None:
        item = self._action_item
        if url is not None:
            self._pick_folder_dialog.set_current_directory(url)
            asyncio.ensure_future(
                self._model.download_async(
                    item.asset_model,
                    url,
                    on_progress_fn=partial(self._on_download_progress, item),
                    callback=partial(self._on_asset_downloaded, item),
                )
            )

        self._download_progress_bar[item].visible = True

        if item in self._hover_center_label:
            self._hover_label[item].text = "Downloading"
        if item in self._hover_label:
            self._hover_center_label[item].text = "Downloading"

    def _on_download_progress(self, item: AssetDetailItem, progress: float) -> None:
        if item in self._download_progress_bar:
            self._download_progress_bar[item].progress = progress

    def _on_asset_downloaded(self, item: AssetDetailItem, results: Dict):
        self._download_progress_bar[item].visible = False

        if results.get("status") != omni.client.Result.OK:
            return

        async def delayed_item_changed(model: AssetStoreModel, item: AssetDetailItem):
            for _ in range(20):
                await omni.kit.app.get_app().next_update_async()
            self.item_changed(model, item)

        url = results.get("url")
        if url:
            # Update asset url, type and tips
            item.url = url
            self._download_helper.save_download_asset(item.asset_model, url)

            item.asset_type = AssetType.NORMAL
            if item in self._asset_type_image:
                (type_image_url, type_image_size) = self._get_asset_type_image(item)
                self._asset_type_image[item].source_url = type_image_url
                self._asset_type_image[item].width = ui.Pixel(type_image_size)
                self._asset_type_image[item].height = ui.Pixel(type_image_size)
            if item in self._hover_center_label:
                self._hover_label[item].text = item.tips
                self._hover_center_label[item].name = item.asset_type
            if item in self._hover_label:
                self._hover_center_label[item].text = item.tips
                self._hover_label[item].name = item.asset_type

            asyncio.ensure_future(self._download_thumbnail(item, url))
            asyncio.ensure_future(delayed_item_changed(self._model, item))
            # Cache the Url in case we click away from this grid view
            self._draggable_urls[item.uid] = url

    async def _download_thumbnail(self, item: AssetDetailItem, dest_url: str):
        """Copies the thumbnail for the given asset to the .thumbs subdir."""
        if not (item and dest_url):
            return
        thumbnail = item.asset_model["thumbnail"]
        thumbnail_ext = os.path.splitext(thumbnail)[-1]
        if not thumbnail_ext:
            return
        filename = os.path.basename(dest_url) + thumbnail_ext
        thumbnail_url = f"{os.path.dirname(dest_url)}/.thumbs/256x256/{filename}"
        thumbnail_url = thumbnail_url.replace(".jpeg", ".png")
        await omni.client.copy_async(thumbnail, thumbnail_url, behavior=omni.client.CopyBehavior.OVERWRITE)

        # Add downloaded to My Assets after thumbnails downloaded to make sure it display well
        self._add_to_my_assets(dest_url)

    def _navigate(self, url: str):
        try:
            import omni.kit.window.content_browser

            content_window = omni.kit.window.content_browser.get_content_window()
            content_window.navigate_to(url)
            content_window._window._window.focus()
        except ImportError:
            pass

    def _on_type_image_pressed(self, item: AssetDetailItem) -> None:
        if item.asset_type == AssetType.EXTERNAL_LINK:
            webbrowser.open(item.asset_model["product_url"])

    def _get_asset_type_image_multiple(self, thumbnail_size):
        if thumbnail_size > 384:
            return 3
        elif thumbnail_size > 192:
            return 2
        else:
            return 1

    def _add_to_my_assets(self, url: str) -> None:
        # Add download folder to My Assets
        for provider, setting in self._model.providers.items():
            if provider == "My Assets":
                url = url.replace("\\", "/")
                downloaded_folder = url[: url.rfind("/")]
                my_assets_folders = self._settings.get(SETTING_MY_ASSET_FOLDERS)
                # Check if download folder already in My Assets
                if my_assets_folders:
                    for folder in my_assets_folders:
                        if downloaded_folder.startswith(folder):
                            # folder already in my assets, require to refresh folder
                            self._settings.set(SETTING_MY_ASSET_FOLDER_CHANGED, folder)
                            return
                    my_assets_folders.append(downloaded_folder)
                else:
                    my_assets_folders = [downloaded_folder]

                # Add download folder to My Assets
                self._settings.set(SETTING_MY_ASSET_FOLDERS, my_assets_folders)

                break
