# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from omni.services.browser.asset

from fastapi import Header


def get_app_header(x_ov_app: str = Header("")):
    pass


def get_app_version(x_ov_version: str = Header("")):
    pass
