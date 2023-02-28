# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
from typing import Dict, List

import json

import carb

from ..models import AssetModel
from .static import StaticAssetStore


class JsonFileAssetStore(StaticAssetStore):
    """ Set of assets from json file.

        Args:
            store_id (str): Unique identifier for the store.
            url (str): Url of json file.
    """

    def __init__(self, store_id: str, url: str) -> None:
        super().__init__(store_id, data=self._load(url))
        self._url = url

    def _load(self, url: str) -> List[AssetModel]:
        asset_json = None
        try:
            with open(url, "r") as json_file:
                asset_json = json.load(json_file)
        except FileNotFoundError:
            carb.log_error(f"Failed to open {url}!")
        except PermissionError:
            carb.log_error(f"Cannot read {url}: permission denied!")
        except Exception as exc:
            carb.log_error(f"Unknown failure to read {url}: {exc}")

        if asset_json is None:
            return []

        assets = asset_json["assets"]
        asset_models: List[AssetModel] = []
        for asset in assets:
            asset_models.append(AssetModel(**asset))

        return asset_models
