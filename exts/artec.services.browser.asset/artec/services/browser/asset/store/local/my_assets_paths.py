# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from omni.kit.browser.asset_provider.local

from functools import lru_cache
import asyncio
from typing import Optional, List, Callable
import carb
import carb.dictionary
import carb.settings
import omni.ui as ui
import omni.kit.app
from omni.kit.window.filepicker import FilePickerDialog

from .style import MY_ASSETS_STYLE

SETTING_MY_ASSET_FOLDERS = "/persistent/exts/omni.kit.browser.asset_provider.local/folders"


class PathItem(ui.AbstractItem):
    def __init__(self, path, add_dummy=False):
        super().__init__()
        self.path_model = ui.SimpleStringModel(path)
        self.add_dummy = add_dummy

    def __repr__(self):
        return f"[PathItem]: {self.path_model.as_string}"


class MyAssetPathsModel(ui.AbstractItemModel):
    def __init__(self, on_path_changed_fn: Callable[[None], None]):
        super().__init__()

        self._on_path_changed_fn = on_path_changed_fn
        self._settings = carb.settings.get_settings()
        self._load()
        self._add_dummy = PathItem("", add_dummy=True)

    def destroy(self):
        self._children = []

    def get_item_children(self, item: Optional[ui.AbstractItem] = None) -> List[ui.AbstractItem]:
        """Returns all the children when the widget asks it."""
        if item is not None:
            return []

        return self._children + [self._add_dummy]

    def get_item_value_model_count(self, item: PathItem):
        """The number of columns"""
        return 3

    def get_item_value_model(self, item: PathItem, column_id: int):
        if column_id == 1:
            return item.path_model
        return None

    def _load(self):
        self._children = []

        folders = self._settings.get(SETTING_MY_ASSET_FOLDERS)
        if folders:
            for folder in folders:
                item = PathItem(folder)
                self._children.append(item)

        self._item_changed(None)

    def add_empty(self):
        self._children.append(PathItem(""))
        self._item_changed(None)

    def add_item(self, item: PathItem):
        self._children.append(item)
        self.save()
        self._item_changed(None)

    def remove_item(self, item: PathItem):
        self._children.remove(item)
        self.save()
        self._item_changed(None)

    def save(self):
        paths = [c.path_model.as_string for c in self._children]
        self._settings.set(SETTING_MY_ASSET_FOLDERS, paths)
        if self._on_path_changed_fn:
            self._on_path_changed_fn()


class MyAssetPathDelegate(ui.AbstractItemDelegate):
    def __init__(self):
        super().__init__()
        self._pick_folder_dialog: Optional[FilePickerDialog] = None

    def destroy(self):
        self._pick_folder_dialog = None

    def build_widget(self, model: MyAssetPathsModel, item: PathItem, column_id: int, level, expanded):
        """Create a widget per column per item"""

        if column_id == 0 and not item.add_dummy:

            def open(item_=item):
                # Import it here instead of on the file root because it has long import time.
                path = item_.path_model.as_string
                if path:
                    import webbrowser

                    webbrowser.open(path)

            ui.Button("open", width=20, clicked_fn=open, tooltip="Open path using OS file explorer.")
        elif column_id == 1 and not item.add_dummy:
            value_model = model.get_item_value_model(item, column_id)
            ui.StringField(value_model)

        elif column_id == 2:

            def on_click(item_=item):
                if item.add_dummy:
                    if self._pick_folder_dialog is None:
                        self._pick_folder_dialog = self._create_filepicker(
                            "Select Directory for My Assets",
                            click_apply_fn=lambda url, m=model: self._on_folder_picked(url, m),
                            dir_only=True,
                        )
                    self._pick_folder_dialog.show()
                else:
                    model.remove_item(item_)

            with ui.HStack(width=60):
                ui.Spacer(width=10)
                ui.Button(
                    name=("add" if item.add_dummy else "remove"),
                    style_type_name_override="ItemButton",
                    width=20,
                    height=20,
                    clicked_fn=on_click,
                )
                ui.Spacer(width=4)

                ui.Spacer()

    def build_header(self, column_id: int):

        COLUMNS = ["", "folder", "edit"]

        with ui.HStack(height=24):
            ui.Spacer(width=10)
            ui.Label(COLUMNS[column_id], name="header")

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

    def _on_folder_picked(self, url: Optional[str], model: ui.AbstractItemModel) -> None:
        item = PathItem(url)
        model.add_item(item)


class MyAssetsPathsWidget(object):
    def __init__(self, on_path_changed_fn: Callable[[None], None]):
        self._model = MyAssetPathsModel(on_path_changed_fn)
        self._delegate = MyAssetPathDelegate()

        with ui.ScrollingFrame(
            horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
            style_type_name_override="TreeView",
        ):
            tree_view = ui.TreeView(self._model, delegate=self._delegate, root_visible=False, header_visible=True)
            tree_view.column_widths = [ui.Pixel(46), ui.Fraction(1), ui.Pixel(60)]

    def destroy(self):
        self._model.destroy()
        self._model = None
        self._delegate.destroy()
        self._delegate = None


class MyAssetsPathsWindow(ui.Window):
    def __init__(self, on_path_changed_fn: Callable[[None], None] = None):
        super().__init__("My Assets Folders", width=500, height=600)

        self._on_path_changed_fn = on_path_changed_fn
        self._widget: Optional[MyAssetsPathsWidget] = None

        self.frame.set_build_fn(self._build_ui)
        self.frame.set_style(MY_ASSETS_STYLE)

    def destroy(self):
        if self._widget is not None:
            self._widget.destroy()
            self._widget = None
        self.visible = False

    def _build_ui(self):
        with self.frame:
            self._widget = MyAssetsPathsWidget(self._on_path_changed_fn)
