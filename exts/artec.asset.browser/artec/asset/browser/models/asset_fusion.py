from dataclasses import dataclass
from .asset_detail_item import AssetDetailItem


@dataclass(frozen=True)
class AssetFusion:
    asset: AssetDetailItem
    name: str
    url: str
