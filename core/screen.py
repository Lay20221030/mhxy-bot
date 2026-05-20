# -*- coding: utf-8 -*-
"""
屏幕捕获与图像识别
通过 WindowGroup 管理多窗口截图
"""

import cv2
import numpy as np
import logging
from typing import Optional, Tuple
from config.settings import MATCH_THRESHOLD

logger = logging.getLogger(__name__)


class ScreenManager:
    """屏幕管理器 - 依赖 WindowGroup"""

    def __init__(self, window_group):
        self.wg = window_group

    def capture(self, window_index: Optional[int] = None):
        """截取窗口"""
        return self.wg.capture(window_index)

    def find_template(self, template_name: str, window_index: Optional[int] = None):
        """在指定窗口查找模板"""
        return self.wg.find_template(template_name, window_index)

    def capture_region(self, window_index: int, x: int, y: int, w: int, h: int) -> np.ndarray:
        """截取指定窗口的局部区域"""
        return self.wg.capture_region(window_index, x, y, w, h)

    def find_quest_markers(self):
        """检测所有窗口的任务标记"""
        return self.wg.detect_quest_markers()

    def find_color_in_window(self, window_index: int, color: Tuple[int, int, int],
                              tolerance: int = 30) -> Optional[Tuple[int, int]]:
        """在指定窗口中查找颜色"""
        screen = self.capture(window_index)
        lower = np.array([max(0, c - tolerance) for c in color])
        upper = np.array([min(255, c + tolerance) for c in color])
        mask = cv2.inRange(screen, lower, upper)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        largest = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)
        return (x + w // 2, y + h // 2)

    def get_color_at(self, window_index: int, x: int, y: int) -> Tuple[int, int, int]:
        """获取指定窗口中某点的颜色"""
        screen = self.capture(window_index)
        h, w = screen.shape[:2]
        if 0 <= y < h and 0 <= x < w:
            return tuple(screen[y, x])
        return (0, 0, 0)


# 全局实例 (需在 main.py 中初始化时传入 window_group)
screen_mgr = None
