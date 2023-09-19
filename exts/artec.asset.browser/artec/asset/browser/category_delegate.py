# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from AssetStore MainNavigationDelegate

from omni import ui
from omni.kit.browser.core import CategoryDelegate, CategoryItem
from .models import MainNavigationItem, AssetStoreModel


class MainNavigationDelegate(CategoryDelegate):
    def __init__(self, model: AssetStoreModel, **kwargs):
        self._model = model
        super().__init__(kwargs)

    def get_label(self, item: CategoryItem) -> str:
        return item.name.upper()

    def build_widget(
        self,
        model: ui.AbstractItemModel,
        item: MainNavigationItem,
        index: int = 0,
        level: int = 0,
        expanded: bool = False,
    ):
        """
        Create a widget per catetory item
        Args:
            model (AbstractItemModel): Category data model
            item (CategoryItem): Category item
            index (int): ignore
            level (int): ignore
            expand (int): ignore
        """
        with ui.HStack():
            if self._tree_mode:
                ui.Label("  " * level, width=0)
            ui.Label(
                self.get_label(item),
                width=0,
                alignment=ui.Alignment.LEFT_CENTER,
                style_type_name_override="TreeView.Item.Name",
            )
            ui.Spacer()
            if item.configurable:
                ui.Button(
                    "",
                    width=16,
                    height=16,
                    clicked_fn=lambda model=model, item=item: self._on_config(model, item),
                    style_type_name_override="TreeView.Item.Button",
                )

    def build_branch(
        self,
        model: ui.AbstractItemModel,
        item: CategoryItem,
        column_id: int = 0,
        level: int = 0,
        expanded: bool = False,
    ):
        """
        Create a branch widget that opens or closes subtree
        Args:
            model (AbstractItemModel): Category data model
            item (CategoryItem): Category item
            column_id (int): ignore
            level (int): ignore
            expand (int): ignore
        """
        if not self._tree_mode or len(item.children) == 0:
            # In tree mode, if have children, show as branch
            return

        with ui.HStack(height=20, spacing=5):
            ui.Label("  " * level, width=0)
            if expanded:
                ui.Label("- ", width=5)
            else:
                ui.Label("+ ", width=5)

    def _on_config(self, model: AssetStoreModel, item: MainNavigationItem) -> None:
        # Here item name is provider id
        self._model.config_provider(item.name)
