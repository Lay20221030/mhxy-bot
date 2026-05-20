# -*- coding: utf-8 -*-
"""
导航模块 - 利用游戏自带寻路系统

操作方式：
1. 按M打开地图
2. 点击目的地（任务NPC位置）
3. 等待角色自动到达
4. 接近NPC后按空格交互
"""

import time
import logging
from typing import Optional, Tuple

import cv2
import numpy as np

from config.settings import NAV, COMMON

logger = logging.getLogger(__name__)


class Navigator:
    """导航器 - 利用游戏内置寻路"""

    def __init__(self, window_group, input_sim, screen_mgr):
        self.wg = window_group
        self.input = input_sim
        self.screen = screen_mgr

    def open_map(self, window_index: int) -> bool:
        """打开地图"""
        logger.debug(f"[号{window_index+1}] 打开地图")
        return self.input.key("m", window_index)

    def close_map(self, window_index: int) -> bool:
        """关闭地图"""
        logger.debug(f"[号{window_index+1}] 关闭地图")
        return self.input.key("m", window_index)

    def toggle_map(self, window_index: int) -> bool:
        """切换地图显示/隐藏"""
        logger.debug(f"[号{window_index+1}] 切换地图")
        return self.input.key("m", window_index)

    def click_map_destination(self, screen_x: int, screen_y: int, window_index: int) -> bool:
        """在地图上点击目的地（屏幕坐标 → 自动转为窗口局部坐标）"""
        local_x, local_y = self.wg.windows[window_index].screen_to_local(screen_x, screen_y)
        logger.debug(f"[号{window_index+1}] 点击地图坐标 ({local_x},{local_y})")
        return self.input.click(local_x, local_y, window_index)

    def check_arrived(self, window_index: int, timeout: float = 10.0) -> bool:
        """检测是否已到达目的地"""
        start = time.time()
        while time.time() - start < timeout:
            if self._check_interactable(window_index):
                return True
            time.sleep(0.5)
        return False

    def _check_interactable(self, window_index: int) -> bool:
        """检测当前角色是否可以与目标NPC交互"""
        region = self.screen.capture_region(window_index, 0, 0,
                                            self.wg.windows[window_index].width, 100)

        yellow = (255, 255, 100)
        lower = [max(0, c - 80) for c in yellow]
        upper = [min(255, c + 80) for c in yellow]
        lower_np = np.array(lower, dtype=np.uint8)
        upper_np = np.array(upper, dtype=np.uint8)
        mask = cv2.inRange(region, lower_np, upper_np)

        pixels = cv2.countNonZero(mask)
        if pixels > 50:
            logger.debug(f"检测到交互提示 ({pixels} 像素)")
            return True
        return False

    def go_to_npc(self, npc_template: str, window_index: int) -> bool:
        """导航到指定NPC"""
        markers = self.screen.wg.detect_quest_markers()
        quest_markers = [(wi, x, y) for wi, x, y in markers if wi == window_index]

        self.toggle_map(window_index)
        time.sleep(0.5)

        if quest_markers:
            _, sx, sy = quest_markers[0]
            self.click_map_destination(sx, sy, window_index)
            logger.info(f"[号{window_index+1}] 点击地图任务标记 @ ({sx},{sy})")
        else:
            cx, cy = self.wg.windows[window_index].center()
            self.click_map_destination(cx, cy, window_index)
            logger.info(f"[号{window_index+1}] 点击地图中心 @ ({cx},{cy})")

        time.sleep(0.5)
        self.toggle_map(window_index)

        logger.info(f"[号{window_index+1}] 自动寻路中...")
        return self.check_arrived(window_index, timeout=NAV.get("auto_path_wait", 5000) / 1000.0)

    def go_to_objective(self, window_index: int) -> bool:
        """导航到当前任务目标"""
        markers = self.screen.wg.detect_quest_markers()
        quest_markers = [(wi, x, y) for wi, x, y in markers if wi == window_index]

        if not quest_markers:
            logger.warning(f"[号{window_index+1}] 未检测到任务标记")
            return False

        _, sx, sy = quest_markers[0]
        self.toggle_map(window_index)
        time.sleep(0.5)
        self.click_map_destination(sx, sy, window_index)
        time.sleep(0.5)
        self.toggle_map(window_index)

        if not self.check_arrived(window_index, timeout=NAV.get("auto_path_wait", 5000) / 1000.0):
            return False

        return self._approach_and_interact(window_index)

    def _approach_and_interact(self, window_index: int) -> bool:
        """接近并交互"""
        time.sleep(NAV.get("approach_wait", 2000) / 1000.0)

        if not self._check_interactable(window_index):
            logger.warning("未检测到可交互目标")
            return False

        logger.info(f"[号{window_index+1}] 检测到可交互NPC，按空格交互")
        return self.input.interact_with_npc(window_index)

    def go_to_next_quest(self, window_index: int = 0) -> bool:
        """导航到下一个任务（通用入口）"""
        logger.info(f"[号{window_index+1}] 查找下一个任务目标...")

        markers = self.screen.wg.detect_quest_markers()
        if not markers:
            logger.info(f"[号{window_index+1}] 暂无任务标记")
            return False

        quest_markers = [(wi, x, y) for wi, x, y in markers if wi == window_index]
        if not quest_markers:
            quest_markers = markers

        if not quest_markers:
            return False

        _, sx, sy = quest_markers[0]
        logger.info(f"[号{window_index+1}] 导航到标记 @ ({sx},{sy})")

        self.toggle_map(window_index)
        time.sleep(0.5)
        self.click_map_destination(sx, sy, window_index)
        time.sleep(0.5)
        self.toggle_map(window_index)

        if not self.check_arrived(window_index, timeout=NAV.get("auto_path_wait", 5000) / 1000.0):
            return False

        return self._approach_and_interact(window_index)
