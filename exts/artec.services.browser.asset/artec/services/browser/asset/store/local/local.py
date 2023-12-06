# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from omni.kit.browser.asset_provider.local class LocalFolderAssetProvider

import asyncio
import carb
import carb.settings
import json
from typing import Dict, List, Optional

from .static import StaticAssetStore
from ...models import AssetModel, ProviderModel
from ...collector import S3Collector
from pathlib import Path

import omni.kit.app

from .my_assets_paths import MyAssetsPathsWindow
from .constants import SETTING_ROOT, SETTING_STORE_ENABLE

CURRENT_PATH = Path(__file__).parent
DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data")

PROVIDER_ID = "My Assets"
SETTING_STORE_RERESH = SETTING_ROOT + "refresh"
SETTING_STORE_SEARCH_SUB_FOLDERS = SETTING_ROOT + "searchSubFolders"
SETTING_STORE_FOLDER = SETTING_ROOT + "folders"
SETTING_PERSISTENT_STORE_FOLDER = "/persistent" + SETTING_STORE_FOLDER
SETTING_STORE_FOLDER_CHANGED = SETTING_ROOT + "folderChanged"

DEFAULT_THUMBNAIL = f"{DATA_PATH}/usd_stage_256.png"
CACHE_FILE = "${shared_documents}/my_assets_2.json"


class LocalFolderAssetProvider(StaticAssetStore):
    """ Local file system asset provider
    """

    def __init__(self):
        super().__init__(PROVIDER_ID, [])
        self._settings = carb.settings.get_settings()
        self._my_assets_window: Optional[MyAssetsPathsWindow] = None
        self._folders = self._get_local_folders()
        self._assets: Dict[str, Dict[str, List[AssetModel]]] = {}
        self._json_file = carb.tokens.get_tokens_interface().resolve(CACHE_FILE)

        # First load assets from saved file
        self._load_assets()

        # Refresh assets in background
        asyncio.ensure_future(self._collect_async(self._folders))

        self._refresh_folders_sub = omni.kit.app.SettingChangeSubscription(
            SETTING_PERSISTENT_STORE_FOLDER,
            lambda item, event_type: self._on_path_changed(),
        )
        self._folder_changed_sub = omni.kit.app.SettingChangeSubscription(
            SETTING_STORE_FOLDER_CHANGED,
            lambda item, event_type: self._on_folder_changed(event_type),
        )

    def destroy(self):
        self._refresh_folders_sub = None
        self._folder_changed_sub = None

        if self._my_assets_window:
            self._my_assets_window.destroy()
            self._my_assets_window = None

    async def _collect_async(self, folders) -> List[AssetModel]:
        # Collection assets from folders into json file
        for url in folders:
            await self._collect_folder_async(url)

        self._save_assets()

    async def _collect_folder_async(self, folder):
        carb.log_info(f"Starting collecting {folder}...")
        if folder not in self._assets:
            self._assets[folder] = {}

        self._scanned_categories = []
        scanner = S3Collector(folder, self._store_id)
        self.__refresh = False
        await scanner.collect(default_thumbnail=DEFAULT_THUMBNAIL, on_folder_done_fn=self._on_folder_collected)
        # OM-77818: Only refresh when whole folder collected instead of refresh every sub folder collected
        if self.__refresh:
            self._refresh_categories()

        # Remove assets not found during collection
        remove_categories = [category for category in self._assets[folder] if category not in self._scanned_categories]
        if remove_categories:
            carb.log_info(f"  Remove {remove_categories} from {folder}")
            for category in remove_categories:
                self._assets[folder].pop(category)
            self._refresh_categories()

    def _filter_by_category(self, categories: List[str]) -> List[AssetModel]:
        search_sub_folders = self._settings.get(SETTING_STORE_SEARCH_SUB_FOLDERS)
        filtered: List[AssetModel] = []
        for _, folder in self._assets.items():
            for _, assets in folder.items():
                if categories:
                    for item in assets:
                        for item_category in item.categories:
                            if search_sub_folders:
                                if any(item_category.lower().startswith(category.lower()) for category in categories):
                                    filtered.append(item)
                                    break
                            else:
                                # Here make sure category is match
                                if any(category.lower() == item_category.lower() for category in categories):
                                    break
                else:
                    filtered.extend(assets)

        return filtered

    def provider(self) -> ProviderModel:
        """Return provider info"""
        return ProviderModel(
            name=self._store_id,
            icon=f"{DATA_PATH}/folder.svg",
            private=True,
            configurable=True,
            refresh_setting=SETTING_STORE_RERESH,
            enable_setting=SETTING_STORE_ENABLE,
        )

    def config(self) -> None:
        """Entry point to config the provider"""
        if self._my_assets_window:
            # Always destroy old window to make sure laod latest settings when show config window
            self._my_assets_window.destroy()

        self._my_assets_window = MyAssetsPathsWindow()

    def _get_local_folders(self) -> List[str]:
        folders = self._settings.get(SETTING_PERSISTENT_STORE_FOLDER)
        if not folders:
            folders = self._settings.get(SETTING_STORE_FOLDER)
        return folders

    def _on_path_changed(self):
        folders = self._get_local_folders()
        if folders != self._folders:
            # Refresh assets
            append_folders = [folder for folder in folders if folder not in self._folders]
            remove_folders = [folder for folder in self._folders if folder not in folders]
            self._folders = folders
            if remove_folders:
                for folder in remove_folders:
                    if folder in self._assets:
                        self._assets.pop(folder)
                self._refresh_categories()
            if append_folders:
                asyncio.ensure_future(self._collect_async(append_folders))

    def _on_folder_changed(self, event_type):
        if event_type != carb.settings.ChangeEventType.CHANGED:
            return
        folder = self._settings.get(SETTING_STORE_FOLDER_CHANGED)
        if folder:
            asyncio.ensure_future(self._collect_async([folder]))

    def _on_folder_collected(self, url: str, asset_models: List[AssetModel]) -> None:
        carb.log_info(f"{url} collected with {len(asset_models)} assets")

        self._scanned_categories.append(url)
        for folder in self._folders:
            if url.startswith(folder):
                break
        else:
            return

        # Append assets
        if url in self._assets[folder]:
            refresh_category = False
            if self._assets[folder][url] == asset_models:
                # Do nothind since assets no change
                return
        else:
            refresh_category = True

        self._assets[folder][url] = asset_models
        self.__refresh = refresh_category

    def _refresh_categories(self) -> None:
        self._load_categories()
        # Notify to refresh
        self._settings.set(SETTING_STORE_RERESH, True)

    def _load_categories(self) -> None:
        # Update categories
        categories = set()
        for _, folder in self._assets.items():
            for _, assets in folder.items():
                for asset in assets:
                    categories.update(asset.categories)

        # Generate category list
        self._categories = {}
        for category in categories:
            folders = category.split("/")
            root = folders[0]
            if root not in self._categories:
                self._categories[root] = []
            if len(folders) > 1:
                sub = "/".join(folders[1:])
                self._categories[root].append(sub)

    def _save_assets(self):
        result = {}
        for folder in self._assets:
            result[folder] = {}
            for category in self._assets[folder]:
                result[folder][category] = []
                for data in self._assets[folder][category]:
                    result[folder][category].append(data.to_dict())
        try:
            with open(self._json_file, "w") as json_file:
                json.dump(result, json_file, indent=4)
                json_file.close()
        except FileNotFoundError:
            carb.log_warn(f"Failed to open {self._json_file}!")
        except PermissionError:
            carb.log_warn(f"Cannot write to {self._json_file}: permission denied!")
        except Exception as e:
            carb.log_warn(f"Unknown failure to write to {self._json_file}: {e}")
        finally:
            if json_file:
                json_file.close()

    def _load_assets(self):
        asset_json = None
        try:
            with open(self._json_file, "r") as json_file:
                asset_json = json.load(json_file)
        except FileNotFoundError:
            carb.log_info(f"Failed to open {self._json_file}!")
        except PermissionError:
            carb.log_error(f"Cannot read {self._json_file}: permission denied!")
        except Exception as exc:
            carb.log_error(f"Unknown failure to read {self._json_file}: {exc}")

        self._assets = {}
        self._categories = {}
        if asset_json is None:
            return

        for folder in asset_json:
            if folder not in self._folders:
                continue
            self._assets[folder] = {}
            for category in asset_json[folder]:
                self._assets[folder][category] = []
                for asset in asset_json[folder][category]:
                    asset_model = AssetModel(**asset)
                    self._assets[folder][category].append(asset_model)

        self._load_categories()
