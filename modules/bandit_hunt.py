# -*- coding: utf-8 -*-
"""
强盗/贼王查找模块 (来自教程第17-21课)

贼王分为野外贼王和房间贼王:
- 野外贼王: 给坐标,到附近后搜索周围
- 房间贼王: 不给坐标,需在房间内巡逻查找

关键技巧:
- 找不到贼王时: 快速开关任务栏 → 刷新坐标提示 → 重试
- 贼王被遮挡时: Ctrl+点击 强制穿透
"""

import time
import logging
from typing import Optional, List, Tuple

import cv2
import numpy as np

from config.settings import TEMPLATES
from core.window_group import WindowGroup
from core.screen import ScreenManager
from core.input_sim import InputSim

logger = logging.getLogger(__name__)


class BanditHuntHandler:
    """强盗/贼王查找器"""

    def __init__(self, window_group: WindowGroup, input_sim: InputSim, screen_mgr: ScreenManager):
        self.wg = window_group
        self.input = input_sim
        self.screen = screen_mgr

    def find_bandit_in_field(self, window_index: int) -> Optional[Tuple[int, int]]:
        """野外查找强盗/贼王

        策略:
        1. 在当前位置周围搜索金色任务标记
        2. 如果找不到 → 快速开关任务栏刷新坐标
        3. 重新移动到新位置再搜索
        """
        logger.info(f"[号{window_index+1}] 野外搜索贼王...")

        for refresh_attempt in range(3):
            # 扫描周围的金色任务标记
            pos = self._scan_surroundings(window_index)
            if pos:
                logger.info(f"找到贼王 @ {pos}")
                return pos

            # 找不到 → 刷新任务栏
            if refresh_attempt < 2:
                logger.debug(f"未找到，刷新任务栏 (尝试{refresh_attempt+1}/3)")
                self._refresh_quest_panel(window_index)

        logger.warning("野外搜索贼王失败")
        return None

    def find_bandit_in_room(self, window_index: int, room_spawn_points: List[Tuple[int, int]] = None
                            ) -> Optional[Tuple[int, int]]:
        """房间内查找贼王（巡逻模式）

        Args:
            window_index: 窗口索引
            room_spawn_points: 房间内可能的刷新点列表
        """
        logger.info(f"[号{window_index+1}] 房间内巡逻查贼王...")

        # 默认巡逻点（房间内常见刷新位置）
        if room_spawn_points is None:
            room_spawn_points = [
                (50, 50), (200, 50), (350, 50),
                (50, 200), (200, 200), (350, 200),
                (50, 350), (200, 350), (350, 350),
            ]

        for i, (px, py) in enumerate(room_spawn_points):
            # 点击房间内位置移动
            self.input.click(px, py, window_index)
            time.sleep(1)

            # 检测周围是否有贼王
            pos = self._scan_surroundings(window_index)
            if pos:
                return pos

            # 每移动几次后重新开关任务栏
            if i % 3 == 2:
                self._refresh_quest_panel(window_index)

        return None

    def _scan_surroundings(self, window_index: int) -> Optional[Tuple[int, int]]:
        """扫描周围区域是否有贼王/强盗"""
        region = self.screen.capture(window_index)

        # 检测金色/黄色任务标记
        lower = np.array([150, 150, 50], dtype=np.uint8)
        upper = np.array([255, 255, 150], dtype=np.uint8)
        mask = cv2.inRange(region, lower, upper)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 50 < area < 5000:
                x, y, w, h = cv2.boundingRect(contour)
                candidates.append((x + w // 2, y + h // 2, area))

        if not candidates:
            return None

        # 选最大的标记（最有可能是任务目标）
        candidates.sort(key=lambda c: c[2], reverse=True)
        return (candidates[0][0], candidates[0][1])

    def _refresh_quest_panel(self, window_index: int):
        """快速开关任务栏刷新坐标提示"""
        self.input.key("j", window_index)
        time.sleep(0.3)
        self.input.key("j", window_index)
        time.sleep(0.3)

    def move_to_bandit_area(self, window_index: int, area_x: int, area_y: int) -> bool:
        """移动到强盗/贼王附近区域（先飞旗再步行）"""
        win = self.wg.windows[window_index]

        # 打开地图点区域
        self.input.key("m", window_index)
        time.sleep(0.5)

        # 点击地图位置
        local_x, local_y = win.screen_to_local(area_x, area_y)
        self.input.click(local_x, local_y, window_index)
        time.sleep(0.5)

        # 关闭地图
        self.input.key("m", window_index)

        # 等待到达
        time.sleep(3)
        return True

    def click_bandit_with_unblock(self, x: int, y: int, window_index: int) -> bool:
        """点击强盗，处理遮挡"""
        from modules.navigation import Navigator
        # 实例化一个简单的navigator用于遮挡处理
        # (直接调用 Ctrl 点击策略)
        for attempt in range(3):
            self.input.click(x, y, window_index)
            time.sleep(0.5)

            if self._check_dialog_open(window_index):
                return True

        # 被遮挡，Ctrl 强制触发
        logger.info("强制 Ctrl 触发对话")
        pyautogui.keyDown("ctrl")
        time.sleep(0.1)
        self.input.click(x, y, window_index)
        time.sleep(0.5)

        import pyautogui
        pyautogui.keyUp("ctrl")

        return self._check_dialog_open(window_index)

    def _check_dialog_open(self, window_index: int) -> bool:
        return self.screen.find_template("dialog_confirm", window_index) is not None


# 全局实例
bandit_hunt_handler = None
