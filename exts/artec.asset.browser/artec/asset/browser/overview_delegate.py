from typing import Optional
import carb.settings
from omni.kit.browser.core import DetailDelegate, CategoryItem


class OverviewDelegate(DetailDelegate):
    def get_label(self, item: CategoryItem) -> Optional[str]:
        return item.name.upper()

    def on_double_click(self, item: CategoryItem) -> None:
        # Show selected category
        settings = carb.settings.get_settings()
        settings.set("/exts/omni.kit.browser.asset_store/showCategory", item.url)
