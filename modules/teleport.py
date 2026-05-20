# -*- coding: utf-8 -*-
"""
传送模块 - 飞行旗/飞行符 (来自教程第12课)

飞行旗:
1. 打开背包 → 找到飞行旗
2. 点击飞行旗 → 显示旗面(多个红点落点)
3. 选择离目的地最近的红点 → 点击传送
4. 关闭背包 → 从落点继续自动寻路

飞行符:
- 直接使用飞行符 → 选择目标地图 → 传送
"""

import time
import logging
from typing import Optional, List, Tuple

import cv2
import numpy as np

from config.settings import NAV, TEMPLATES
from core.window_group import WindowGroup
from core.screen import ScreenManager
from core.input_sim import InputSim

logger = logging.getLogger(__name__)


class TeleportHandler:
    """传送处理器"""

    def __init__(self, window_group: WindowGroup, input_sim: InputSim, screen_mgr: ScreenManager):
        self.wg = window_group
        self.input = input_sim
        self.screen = screen_mgr

    # ─── 飞行旗 ──────────────────────────────

    def use_fly_flag(self, window_index: int, dest_map_x: int, dest_map_y: int) -> bool:
        """使用飞行旗传送到最近的红点

        Args:
            window_index: 窗口索引
            dest_map_x, dest_map_y: 目的地游戏坐标

        Returns:
            传送是否成功
        """
        logger.info(f"[号{window_index+1}] 尝试使用飞行旗传送到 ({dest_map_x},{dest_map_y})")

        # 1. 打开背包
        if not self._open_backpack(window_index):
            return False

        # 2. 找到飞行旗并点击
        flag_pos = self._find_fly_flag(window_index)
        if not flag_pos:
            logger.warning("背包中未找到飞行旗")
            self.input.key("escape", window_index)
            return False

        self.input.click(flag_pos[0], flag_pos[1], window_index)
        time.sleep(0.8)

        # 3. 在旗面上找到所有红点
        red_dots = self._find_red_dots(window_index)
        if not red_dots:
            logger.warning("旗面未找到红点")
            self.input.key("escape", window_index)
            return False

        logger.info(f"找到 {len(red_dots)} 个红点落点")

        # 4. 选择离目的地最近的红点
        nearest = self._find_nearest_dot(red_dots, dest_map_x, dest_map_y)
        if nearest:
            self.input.click(nearest[0], nearest[1], window_index)
            time.sleep(1)
            logger.info(f"已传送到红点 @ ({nearest[0]},{nearest[1]})")
        else:
            # 选第一个作为兜底
            self.input.click(red_dots[0][0], red_dots[0][1], window_index)
            time.sleep(1)

        # 5. 关闭背包
        self.input.key("escape", window_index)
        time.sleep(0.5)

        return True

    def _open_backpack(self, window_index: int) -> bool:
        """打开背包"""
        self.input.key("i", window_index)
        time.sleep(0.5)

        # 检测背包是否真的打开了（通过模板匹配）
        opened = self.screen.find_template("backpack_open", window_index)
        return opened is not None

    def _find_fly_flag(self, window_index: int) -> Optional[Tuple[int, int]]:
        """在背包中找到飞行旗"""
        # 模板匹配
        pos = self.screen.find_template("fly_flag_icon", window_index)
        if pos:
            return pos

        # 兜底：颜色检测（飞行旗通常是绿色/蓝色系）
        region = self.screen.capture(window_index)
        lower = np.array([50, 100, 50], dtype=np.uint8)
        upper = np.array([150, 200, 150], dtype=np.uint8)
        mask = cv2.inRange(region, lower, upper)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if 300 < area < 5000:
                x, y, w, h = cv2.boundingRect(contour)
                return (x + w // 2, y + h // 2)

        return None

    def _find_red_dots(self, window_index: int) -> List[Tuple[int, int]]:
        """找旗面上所有红点（飞行落点）"""
        region = self.screen.capture(window_index)

        # 红点颜色范围
        lower = np.array([0, 0, 150], dtype=np.uint8)
        upper = np.array([80, 80, 255], dtype=np.uint8)
        mask = cv2.inRange(region, lower, upper)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        dots = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 10 < area < 500:  # 红点很小
                x, y, w, h = cv2.boundingRect(contour)
                dots.append((x + w // 2, y + h // 2))

        # 按坐标排序（从上到下，从左到右）
        dots.sort(key=lambda p: (p[1], p[0]))
        return dots

    def _find_nearest_dot(self, dots: List[Tuple[int, int]],
                          dest_x: int, dest_y: int) -> Optional[Tuple[int, int]]:
        """找到离目的地最近的红点

        简化：选择最后几个红点之一（通常是较远的地图位置）
        或通过红点颜色判断区域
        """
        if not dots:
            return None

        # 如果没有目的地信息，选中间的红点
        if dest_x == 0 and dest_y == 0:
            return dots[len(dots) // 2]

        # 计算距离最近的红点（简单欧氏距离）
        min_dist = float('inf')
        nearest = dots[0]
        for dot in dots:
            dist = (dot[0] - dest_x) ** 2 + (dot[1] - dest_y) ** 2
            if dist < min_dist:
                min_dist = dist
                nearest = dot

        return nearest

    # ─── 飞行符 ──────────────────────────────

    def use_fly_scroll(self, window_index: int, dest_map: str) -> bool:
        """使用飞行符传送到指定地图

        Args:
            window_index: 窗口索引
            dest_map: 目标地图名 (如 '长安城', '建邺城', '傲来国')

        Returns:
            传送是否成功
        """
        logger.info(f"[号{window_index+1}] 使用飞行符飞往 {dest_map}")

        # 1. 打开背包
        if not self._open_backpack(window_index):
            return False

        # 2. 找到飞行符并点击
        scroll_pos = self._find_fly_scroll(window_index)
        if not scroll_pos:
            logger.warning("背包中未找到飞行符")
            self.input.key("escape", window_index)
            return False

        self.input.click(scroll_pos[0], scroll_pos[1], window_index)
        time.sleep(0.8)

        # 3. 在地图列表中选择目标地图
        map_pos = self._find_map_in_list(window_index, dest_map)
        if map_pos:
            self.input.click(map_pos[0], map_pos[1], window_index)
            time.sleep(1)

        # 4. 关闭弹窗
        self.input.key("escape", window_index)
        time.sleep(0.5)

        return True

    def _find_fly_scroll(self, window_index: int) -> Optional[Tuple[int, int]]:
        """在背包中找到飞行符"""
        pos = self.screen.find_template("fly_scroll_icon", window_index)
        if pos:
            return pos

        # 兜底：颜色检测（飞行符通常是黄色/橙色）
        region = self.screen.capture(window_index)
        lower = np.array([100, 150, 200], dtype=np.uint8)
        upper = np.array([200, 220, 255], dtype=np.uint8)
        mask = cv2.inRange(region, lower, upper)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if 300 < area < 5000:
                x, y, w, h = cv2.boundingRect(contour)
                return (x + w // 2, y + h // 2)

        return None

    def _find_map_in_list(self, window_index: int, map_name: str) -> Optional[Tuple[int, int]]:
        """在地图列表中查找目标地图"""
        # 检测地图列表中的文字区域
        region = self.screen.capture(window_index)

        # 地图列表通常在屏幕中央
        h, w = region.shape[:2]
        list_region = region[h//4:3*h//4, w//4:3*w//4]

        # 检测白色文字区域（地图名）
        gray = cv2.cvtColor(list_region, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x, y, cw, ch = cv2.boundingRect(contour)
            if 50 < cw < 300 and 15 < ch < 40:
                # 返回相对于窗口的坐标
                global_x = w//4 + x + cw // 2
                global_y = h//4 + y + ch // 2
                return (global_x, global_y)

        return None

    # ─── 综合传送入口 ─────────────────────────

    def teleport_to(self, window_index: int, dest_map_x: int = 0,
                    dest_map_y: int = 0, prefer_flag: bool = True) -> bool:
        """综合传送：优先用飞行旗，失败用飞行符

        Args:
            window_index: 窗口索引
            dest_map_x, dest_map_y: 目的地游戏坐标
            prefer_flag: True=优先飞行旗, False=优先飞行符

        Returns:
            传送是否成功
        """
        if prefer_flag:
            # 先试飞行旗
            if self.use_fly_flag(window_index, dest_map_x, dest_map_y):
                return True
            # 失败则尝试飞行符到最近主城
            logger.info("飞行旗失败，尝试飞行符...")
            return self.use_fly_scroll(window_index, "长安城")

        return self.use_fly_scroll(window_index, "长安城")


# 全局实例
teleport_handler = None
