# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from AssetStore class HoverWindow

from typing import Optional
from omni import ui

from .models import AssetDetailItem
from .style import HOVER_WINDOW_STYLE


class HoverWindow(ui.Window):
    """
    Window to show hover for asset item.
    """

    def __init__(self):
        flags = (
            ui.WINDOW_FLAGS_NO_COLLAPSE
            | ui.WINDOW_FLAGS_NO_TITLE_BAR
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_CLOSE
            | ui.WINDOW_FLAGS_NO_DOCKING
        )

        super().__init__(
            "ASSET HOVER WINDOW",
            width=250,
            height=200,
            flags=flags,
            padding_x=0,
            padding_y=0,
            dockPreference=ui.DockPreference.DISABLED,
        )
        self.frame.set_style(HOVER_WINDOW_STYLE)
        self.frame.set_build_fn(self._build_ui)

        self.visible = False

        self._item: Optional[AssetDetailItem] = None
        self._image: Optional[ui.Image] = None

    def _build_ui(self) -> None:
        with self.frame:
            self._container = ui.VStack()
            with self._container:
                self._image = ui.Image(
                    self._item.thumbnail,
                    fill_policy=ui.FillPolicy.PRESERVE_ASPECT_CROP,
                    style_type_name_override="GridView.Image",
                )
                self._build_tips(self._item)

            self._container.set_mouse_hovered_fn(self._on_hover)

    def show(self, item: AssetDetailItem, image_size: float, tips_height, x: float, y: float):
        self._item = item
        if self._image:
            self._image.source_url = item.thumbnail
            self._tips.text = item.tips
            self._tips.name = item.asset_type

        self.width = image_size
        self.height = image_size + tips_height
        self.position_x = x
        self.position_y = y
        self.visible = True

    def _on_hover(self, hovered):
        self.visible = hovered

    def _build_tips(self, item: AssetDetailItem) -> None:
        # Hover background and text
        with ui.ZStack(height=self.height - self.width):
            ui.Rectangle(style_type_name_override="GridView.Item.Hover.Background")
            self._tips = ui.Label(
                item.tips,
                name=item.asset_type,
                alignment=ui.Alignment.CENTER,
                style_type_name_override="GridView.Item.Tips.Text",
            )
