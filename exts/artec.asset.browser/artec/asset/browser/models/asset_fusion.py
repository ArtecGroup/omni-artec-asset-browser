from .asset_detail_item import AssetDetailItem


class AssetFusion:
    def __init__(self, asset: AssetDetailItem, name: str, url: str):
        self.name = name
        self.url = url
        self.asset = asset