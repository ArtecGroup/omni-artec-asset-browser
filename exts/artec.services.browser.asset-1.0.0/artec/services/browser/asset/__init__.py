# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
from .extension import AssetServiceExtension, get_instance
from .models import AssetModel, SearchCriteria, ProviderModel
from .store import BaseAssetStore, StaticAssetStore, JsonFileAssetStore
from .collector import S3Collector