# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Forked from AssetStore class DownloadProgressBar

import carb.events
from omni import ui
import omni.kit.app


class DownloadProgressBar(ui.ProgressBar):
    """
    Represent the asset download progress bar.
    Args:
        real_progress (bool): True to display real progress. False to display progress when time changed.
    """

    def __init__(self, real_progress: bool = True):
        self._real_progress = real_progress
        self._build_ui()

    def destroy(self) -> None:
        self._stop()

    @property
    def visible(self) -> bool:
        return self._container.visible

    @visible.setter
    def visible(self, value: bool) -> bool:
        self._container.visible = value
        if value:
            if self._real_progress:
                self.progress = 0
            else:
                self._start()
        else:
            if self._real_progress:
                self.progress = 1
            else:
                self._stop()

    @property
    def progress(self) -> float:
        return self._progress_bar.model.as_float

    @progress.setter
    def progress(self, value: float) -> None:
        self._progress_bar.model.set_value(value)

    def _start(self) -> None:
        self._progress_bar.model.set_value(0)
        self._action_time = 0.0
        self._current_time = 0.0
        self._step = 0.01
        self._threshold = self._get_threshold()

        self._update_sub = (
            omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(self._update_progress)
        )

    def _stop(self) -> None:
        self._progress_bar.model.set_value(1)
        self._update_sub = None

    def _build_ui(self) -> None:
        self._container = ui.VStack(visible=False)
        with self._container:
            ui.Spacer()
            self._progress_bar = ui.ProgressBar(height=0, style_type_name_override="GridView.Item.Download")

    def _update_progress(self, event: carb.events.IEvent):
        self._current_time += event.payload["dt"]
        if self._current_time - self._action_time >= 0.1:
            value = self._progress_bar.model.as_float
            value += self._step
            if value > 1.0:
                value = 0
            self._progress_bar.model.set_value(value)
            if value >= self._threshold:
                self._step /= 10
                self._threshold = self._get_threshold()
            self._action_time = self._current_time

    def _get_threshold(self):
        value = self._progress_bar.model.as_float
        return value + (1 - value) * 0.75
