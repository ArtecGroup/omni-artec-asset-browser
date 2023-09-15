# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from AssetStore AssetType, AssetDetailItem, MoreDetailItem, SearchingDetailItem

import re
import omni.client
from artec.services.browser.asset import AssetModel
from omni.kit.browser.core import DetailItem
from artec.services.browser.asset import get_instance as get_asset_services

from ..style import ICON_PATH
from ..download_helper import DownloadHelper


class AssetType:
    # External link in product url
    EXTERNAL_LINK = "ExternalLink"

    # Asset in usdz or zip, to be downloaded and unzip if zip
    DOWNLOAD = "Download"

    # Normal, user could drag it into viewport
    NORMAL = "Normal"

    UNKNOWN = "Unknown"


ASSET_TIPS = {
    AssetType.EXTERNAL_LINK: "DOUBLE CLICK FOR\nEXTERNAL LINK",  # Artec Cloud provides external links
    AssetType.DOWNLOAD: "DOUBLE CLICK TO\nDOWNLOAD",  # Default action for download type is to open
    AssetType.NORMAL: "DRAG INTO\nVIEWPORT",
    AssetType.UNKNOWN: "",
}


class AssetDetailItem(DetailItem):
    def __init__(self, asset_model: AssetModel):
        self._local_url = DownloadHelper().get_download_url(asset_model)
        super().__init__(
            asset_model["name"],
            self._local_url if self._local_url else asset_model["download_url"],
            thumbnail=asset_model["thumbnail"]
        )
        self.uid = asset_model["identifier"]
        self.user = asset_model["user"]
        self.asset_model = asset_model

        self._get_type()

    @property
    def tips(self) -> str:
        return ASSET_TIPS[self.asset_type]

    def _get_type(self):
        download_url = self.asset_model["download_url"].split("?")[0]
        if self._local_url:
            self.asset_type = AssetType.NORMAL
        elif download_url:
            if self._is_local_path(download_url):
                # For local assets, drag and drop into viewport
                self.asset_type = AssetType.NORMAL
            elif (
                download_url.lower().endswith("usdz")
                or download_url.lower().endswith("zip")
                or download_url.lower().endswith("download")
            ):
                self.asset_type = AssetType.DOWNLOAD
            else:
                self.asset_type = AssetType.NORMAL
        elif self.asset_model["product_url"]:
            self.asset_type = AssetType.EXTERNAL_LINK
        else:
            self.asset_type = AssetType.UNKNOWN

    def authorized(self) -> bool:
        asset_services = get_asset_services()
        if asset_services:
            asset_store = asset_services.get_store(self.asset_model.get("vendor"))
            if asset_store:
                return asset_store.authorized()
        return False

    def _is_local_path(self, path: str) -> bool:
        """Returns True if given path is a local path"""
        broken_url = omni.client.break_url(path)
        if broken_url.scheme == "file":
            return True
        elif broken_url.scheme in ["omniverse", "http", "https"]:
            return False
        # Return True if root directory looks like beginning of a Linux or Windows path
        root_name = broken_url.path.split("/")[0]
        return not root_name or re.match(r"[A-Za-z]:", root_name) is not None


class MoreDetailItem(DetailItem):
    def __init__(self):
        super().__init__("More", "", f"{ICON_PATH}/load_more.png")

        # used to show tips
        self.tips = "DOUBLE CLICK FOR\nMORE ASSETS"
        self.asset_type = AssetType.NORMAL


class SearchingDetailItem(DetailItem):
    def __init__(self):
        super().__init__("Searching", "", f"{ICON_PATH}/search.png")

        # used to show tips
        self.tips = "Searching"
        self.asset_type = AssetType.NORMAL
