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

    def __init__(self, window_group, input_sim, screen_mgr, teleport=None, station_coach=None):
        self.wg = window_group
        self.input = input_sim
        self.screen = screen_mgr
        self.teleport = teleport           # TeleportHandler 实例
        self.station_coach = station_coach  # StationCoachHandler 实例

        # 位置缓存 — 避免重复飞行 (教程第28课优化)
        self._pos_cache: dict = {}  # {window_idx: {"map": str, "x": int, "y": int}}

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

    # ─── 地图坐标映射 (来自教程第11课) ──────────────────────

    def calc_map_ratio(self, window_index: int, map_width: int, map_height: int,
                       max_map_x: int, max_map_y: int) -> Tuple[float, float]:
        """计算地图坐标与像素的比例

        公式: ratio_x = max_map_x / map_width
              ratio_y = max_map_y / map_height
        然后: pixel_x = dest_x / ratio_x, pixel_y = dest_y / ratio_y

        注意: Y轴是倒的(原点在顶部,数值往下增大)
        """
        ratio_x = max_map_x / map_width
        ratio_y = max_map_y / map_height
        return ratio_x, ratio_y

    def game_to_map_pixel(self, game_x: int, game_y: int,
                          ratio_x: float, ratio_y: float) -> Tuple[int, int]:
        """游戏坐标 → 地图上的像素位置"""
        pixel_x = int(game_x / ratio_x)
        pixel_y = int(game_y / ratio_y)
        return pixel_x, pixel_y

    # ─── 坐标点击偏移计算 (来自教程第14课) ──────────────────

    def calc_click_position(self, base_x: int, base_y: int,
                            current_x: int, current_y: int,
                            npc_x: int, npc_y: int,
                            scale_factor: float = 1.0) -> Tuple[int, int]:
        """计算强盗/NPC 的点击位置

        公式: click_x = base_x + (current_x - npc_x) * scale_factor
              click_y = base_y + (current_y - npc_y) * scale_factor
        """
        click_x = int(base_x + (current_x - npc_x) * scale_factor)
        click_y = int(base_y + (current_y - npc_y) * scale_factor)
        return click_x, click_y

    # ─── 遮挡处理 (来自教程第15课) ──────────────────────────

    def click_with_unblock(self, x: int, y: int, window_index: int,
                           max_retries: int = 3) -> bool:
        """点击目标，处理遮挡情况

        策略:
        1. 先直接点击 (最多 max_retries 次)
        2. 每次点击后检测是否有对话框弹出
        3. 如果 3 次都没成功 → 按 Ctrl + 点击 (强制穿透遮挡)
        """
        for attempt in range(max_retries):
            # 等待角色停止移动再点击
            self._wait_not_moving(window_index)

            self.input.click(x, y, window_index)
            time.sleep(0.5)

            # 检测是否触发了对话框
            if self._check_interactable(window_index):
                return True

            if self._check_dialog_open(window_index):
                return True

        # 3 次都失败 → Ctrl + 点击 (穿透遮挡触发对话)
        logger.info(f"[号{window_index+1}] 被遮挡，使用 Ctrl 强制触发")
        self.input.key("ctrl", window_index)  # 按住 Ctrl
        time.sleep(0.1)
        self.input.click(x, y, window_index)
        time.sleep(0.5)

        return self._check_interactable(window_index) or self._check_dialog_open(window_index)

    def _check_dialog_open(self, window_index: int) -> bool:
        """检测是否有对话框打开"""
        return self.screen.find_template("dialog_confirm", window_index) is not None

    def _wait_not_moving(self, window_index: int, timeout: float = 3.0):
        """等待角色停止移动"""
        start = time.time()
        last_pos = None

        while time.time() - start < timeout:
            # 检测角色位置是否有变化 (简化: 检测两次截图差异)
            region = self.screen.capture_region(window_index, 0, 0,
                                                self.wg.windows[window_index].width, 50)
            current_hash = hash(region.tobytes())

            if last_pos is not None and current_hash == last_pos:
                return  # 位置没变,已停止

            last_pos = current_hash
            time.sleep(0.3)

    def go_to_next_quest(self, window_index: int = 0, dest_x: int = 0,
                          dest_y: int = 0) -> bool:
        """导航到下一个任务（通用入口）

        策略：远距离先用飞行旗/飞行符传送到最近点，再短距离自动寻路
        """
        logger.info(f"[号{window_index+1}] 查找下一个任务目标...")

        # 1. 位置缓存检查 — 如果已在目标附近，跳过传送
        cache = self._pos_cache.get(window_index, {})
        if cache and dest_x > 0 and dest_y > 0:
            # 检查是否在目的地附近（误差范围内）
            cached_x, cached_y = cache.get("x", 0), cache.get("y", 0)
            if abs(cached_x - dest_x) < NAV.get("map_width", 545) // 10 and \
               abs(cached_y - dest_y) < NAV.get("map_height", 276) // 10:
                logger.debug(f"[号{window_index+1}] 已在目标附近，跳过传送")
                # 直接步行即可
                pass
            else:
                # 2. 远距离传送链路：飞行旗 → 驿站 → 步行
                if self.teleport:
                    if not self.teleport.teleport_to(window_index, dest_x, dest_y, prefer_flag=True):
                        if self.station_coach:
                            self.station_coach.go_to_map_via_coach(window_index, "大唐国境")
                    time.sleep(1)
        elif self.teleport and (dest_x > 0 or dest_y > 0):
            if not self.teleport.teleport_to(window_index, dest_x, dest_y, prefer_flag=True):
                if self.station_coach:
                    self.station_coach.go_to_map_via_coach(window_index, "大唐国境")
            time.sleep(1)

        # 更新位置缓存
        self._pos_cache[window_index] = {"x": dest_x, "y": dest_y}

        # 2. 检测任务标记并在地图上导航
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
