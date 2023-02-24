from typing import Dict, Optional
import os
import carb
import carb.tokens
import json
import omni.client
from artec.services.browser.asset import AssetModel


DOWNLOAD_RESULT_FILE = "asset_store_downloads.json"


def Singleton(class_):
    """A singleton decorator"""
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


@Singleton
class DownloadHelper:
    """
    Helper to download assets.
    """

    def __init__(self):
        self._download_root = os.path.abspath(carb.tokens.get_tokens_interface().resolve("${shared_documents}"))
        self._download_result_file = self._download_root + "/" + DOWNLOAD_RESULT_FILE
        self._download_stats: Dict[str, Dict[str, Dict]] = {}

        self._load_download_assets()

    def destroy(self):
        pass

    def get_download_url(self, asset: AssetModel) -> Optional[str]:
        """
        Query asset local downloaded url.
        Args:
            asset (AssetModel): Asset model to query
        Return:
            Local url if found. Else None.
        """
        if asset["vendor"] not in self._download_stats:
            return None
        if asset["identifier"] in self._download_stats[asset["vendor"]]:
            url = self._download_stats[asset["vendor"]][asset["identifier"]]
            (result, entry) = omni.client.stat(url)
            if result == omni.client.Result.OK:
                return url
            else:
                # File not found, clean download stats
                del self._download_stats[asset["vendor"]][asset["identifier"]]
                self._save_download_assets()
        
        return None
            
    def save_download_asset(self, asset: AssetModel, url: str) -> None:
        """
        Save asset local downloaded url
        Args:
            asset (AssetModel): Asset model to save.
            url (str): Local url of downloaded asset model.
        """
        if asset["vendor"] not in self._download_stats:
            self._download_stats[asset["vendor"]] = {}
        self._download_stats[asset["vendor"]][asset["identifier"]] = url
        self._save_download_assets()

    def _save_download_assets(self):
        json_file = None
        try:
            with open(self._download_result_file, "w") as json_file:
                json.dump(self._download_stats, json_file, indent=4)
                json_file.close()
        except FileNotFoundError:
            carb.log_warn(f"Failed to open {self._download_result_file}!")
        except PermissionError:
            carb.log_warn(f"Cannot write to {self._download_result_file}: permission denied!")
        except Exception:
            carb.log_warn(f"Unknown failure to write to {self._download_result_file}")
        finally:
            if json_file:
                json_file.close()

    def _load_download_assets(self):
        result, entry = omni.client.stat(self._download_result_file)
        if result != omni.client.Result.OK:
            self._download_stats = {}
            return
        try:
            with open(self._download_result_file, "r") as json_file:
                self._download_stats = json.load(json_file)
        except FileNotFoundError:
            carb.log_error(f"Failed to open {self._download_result_file}!")
        except PermissionError:
            carb.log_error(f"Cannot read {self._download_result_file}: permission denied!")
        except Exception as exc:
            carb.log_error(f"Unknown failure to read {self._download_result_file}: {exc}")
