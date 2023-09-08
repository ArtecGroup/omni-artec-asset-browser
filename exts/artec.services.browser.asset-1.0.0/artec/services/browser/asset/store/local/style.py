# Forked from omni.kit.browser.asset_provider.local

from pathlib import Path

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("icons")


MY_ASSETS_STYLE = {
    "TreeView": {"background_color": 0xFF23211F, "background_selected_color": 0xFF444444},
    "TreeView.Item": {"margin": 14, "color": 0xFF000055},
    # "Field": {"background_color": 0xFF333322},
    "Label::header": {"margin": 4},
    "Label": {"margin": 5},
    "Label::builtin": {"color": 0xFF909090},
    "Label::config": {"color": 0xFFDDDDDD},
    "ItemButton": {"padding": 2, "background_color": 0xFF444444, "border_radius": 4},
    "ItemButton.Image::add": {"image_url": f"{ICON_PATH}/plus.svg", "color": 0xFF06C66B},
    "ItemButton.Image::remove": {"image_url": f"{ICON_PATH}/trash.svg", "color": 0xFF1010C6},
    "ItemButton.Image::clean": {"image_url": f"{ICON_PATH}/broom.svg", "color": 0xFF5EDAFA},
    "ItemButton.Image::update": {"image_url": f"{ICON_PATH}/refresh.svg", "color": 0xFF5EDAFA},
    "ItemButton:hovered": {"background_color": 0xFF333333},
    "ItemButton:pressed": {"background_color": 0xFF222222},
}
