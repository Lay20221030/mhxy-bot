# -*- coding: utf-8 -*-
"""
藏宝图自动挖掘脚本

流程：
1. 打开背包 (I) → 找到藏宝图
2. 使用藏宝图 → 地图显示标记点
3. 点击标记点 → 自动寻路到达
4. 接近后交互 (空格) → 挖掘
5. 领取奖励 → 关闭弹窗
6. 循环执行

藏宝图特点：
- 每张图有固定坐标，显示在小地图上
- 挖掘需要走到指定位置
- 可能有多个奖励（元宝、装备、宠物等）
"""

import time
import logging
from typing import Optional, List, Tuple

import cv2
import numpy as np

from config.settings import NAV, COMBAT, TEMPLATES
from core.window_group import WindowGroup
from core.screen import ScreenManager
from core.input_sim import InputSim

logger = logging.getLogger(__name__)


class TreasureMapHandler:
    """藏宝图处理器"""

    def __init__(self, window_group: WindowGroup, input_sim: InputSim, screen_mgr: ScreenManager):
        self.wg = window_group
        self.input = input_sim
        self.screen = screen_mgr

    def run(self, max_maps: int = 10) -> bool:
        """执行藏宝图挖掘循环"""
        logger.info(f"=== 开始刷藏宝图 (最多 {max_maps} 张) ===")

        success_count = 0
        for i in range(max_maps):
            logger.info(f"--- 第 {i + 1}/{max_maps} 张 ---")

            # 1. 使用藏宝图
            if not self._use_treasure_map():
                logger.warning("未找到藏宝图或无法使用")
                break

            # 2. 导航到标记点并挖掘
            if self._navigate_and_dig():
                # 3. 领取奖励
                self._collect_rewards()
                success_count += 1

                # 检查是否还有藏宝图
                if not self._has_more_maps():
                    logger.info("藏宝图已用完")
                    break

                time.sleep(2)  # 等待下一张
            else:
                logger.warning("挖掘失败")
                break

        logger.info(f"=== 藏宝图完成: {success_count}/{max_maps} 张 ===")
        return success_count > 0

    def _use_treasure_map(self) -> bool:
        """使用藏宝图"""
        logger.info("[藏宝图] 打开背包...")

        # 按 I 打开背包
        self.input.key("i")
        time.sleep(1)

        # 检测藏宝图图标
        map_pos = self._find_treasure_map_icon()
        if not map_pos:
            logger.warning("[藏宝图] 背包中未找到藏宝图")
            self.input.key("escape")  # 关闭背包
            return False

        # 点击藏宝图使用
        logger.info(f"[藏宝图] 找到藏宝图 @ {map_pos}")
        self.input.click(map_pos[0], map_pos[1])
        time.sleep(1)

        # 点击确认使用
        btn = self.screen.find_template("dialog_confirm")
        if btn:
            self.input.click(btn[0], btn[1])
            time.sleep(1)

        # 关闭背包
        self.input.key("escape")
        time.sleep(0.5)

        return True

    def _find_treasure_map_icon(self) -> Optional[Tuple[int, int]]:
        """在背包中查找藏宝图图标"""
        # 方法1：模板匹配（如果有模板）
        pos = self.screen.find_template("treasure_map_icon")
        if pos:
            return pos

        # 方法2：颜色检测（藏宝图图标通常是棕色/金色）
        region = self.screen.capture()
        brown_lower = np.array([100, 80, 50], dtype=np.uint8)
        brown_upper = np.array([200, 160, 100], dtype=np.uint8)
        mask = cv2.inRange(region, brown_lower, brown_upper)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if 500 < area < 5000:
                x, y, w, h = cv2.boundingRect(contour)
                return (x + w // 2, y + h // 2)

        return None

    def _navigate_and_dig(self) -> bool:
        """导航到标记点并挖掘"""
        logger.info("[藏宝图] 导航到标记点...")

        # 1. 打开地图，点击标记点
        self.input.key("m")
        time.sleep(0.5)

        # 2. 检测地图上的标记点（黄色/金色）
        marker_pos = self._find_map_marker()
        if not marker_pos:
            logger.warning("[藏宝图] 未找到地图标记点")
            self.input.key("m")
            return False

        # 3. 点击标记点设置目的地
        self.input.click(marker_pos[0], marker_pos[1])
        time.sleep(0.5)

        # 4. 关闭地图
        self.input.key("m")
        time.sleep(1)

        # 5. 等待自动寻路到达
        logger.info("[藏宝图] 自动寻路中...")
        if not self._wait_arrived(timeout=15):
            logger.warning("[藏宝图] 寻路超时")
            return False

        # 6. 接近并挖掘
        time.sleep(NAV.get("approach_wait", 2000) / 1000.0)
        return self._dig_treasure()

    def _find_map_marker(self) -> Optional[Tuple[int, int]]:
        """在地图上查找标记点"""
        # 标记点通常是黄色/金色，位于地图中央区域
        region = self.screen.capture()
        h, w = region.shape[:2]

        # 截取地图中央区域（藏宝图标记通常在中央）
        map_region = region[int(h * 0.2):int(h * 0.8), int(w * 0.2):int(w * 0.8)]

        # 检测黄色标记
        yellow_lower = np.array([150, 150, 50], dtype=np.uint8)
        yellow_upper = np.array([255, 255, 150], dtype=np.uint8)
        mask = cv2.inRange(map_region, yellow_lower, yellow_upper)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if 100 < area < 3000:
                x, y, w_c, h_c = cv2.boundingRect(contour)
                # 转换回全屏坐标
                global_x = int(w * 0.2) + x + w_c // 2
                global_y = int(h * 0.2) + y + h_c // 2
                return (global_x, global_y)

        return None

    def _wait_arrived(self, timeout: float = 15.0) -> bool:
        """等待到达目的地"""
        start = time.time()
        while time.time() - start < timeout:
            if self._check_interactable():
                return True
            time.sleep(0.5)
        return False

    def _check_interactable(self) -> bool:
        """检测是否可交互（挖掘点）"""
        region = self.screen.capture()
        h, w = region.shape[:2]

        # 检测屏幕中央下方的交互提示
        bottom_region = region[int(h * 0.6):int(h * 0.9), int(w * 0.3):int(w * 0.7)]

        yellow_lower = np.array([150, 150, 50], dtype=np.uint8)
        yellow_upper = np.array([255, 255, 150], dtype=np.uint8)
        mask = cv2.inRange(bottom_region, yellow_lower, yellow_upper)

        pixels = cv2.countNonZero(mask)
        return pixels > 30

    def _dig_treasure(self) -> bool:
        """挖掘藏宝图"""
        logger.info("[藏宝图] 挖掘...")

        # 按空格交互
        self.input.interact_with_npc()
        time.sleep(1)

        # 检测挖掘动画/结果
        result = self.screen.find_template("dialog_confirm")
        if result:
            self.input.click(result[0], result[1])
            time.sleep(1)

        return True

    def _collect_rewards(self):
        """领取奖励"""
        logger.info("[藏宝图] 领取奖励...")

        # 点击所有奖励按钮
        for _ in range(5):
            btn = self.screen.find_template("dialog_confirm")
            if btn:
                self.input.click(btn[0], btn[1])
                time.sleep(1)
            else:
                break

        # 关闭弹窗
        self.input.esc(count=2)
        time.sleep(1)

    def _has_more_maps(self) -> bool:
        """检查是否还有藏宝图"""
        # 打开背包查看
        self.input.key("i")
        time.sleep(0.5)

        has_map = self._find_treasure_map_icon()
        if not has_map:
            self.input.key("escape")

        return has_map is not None


# 全局实例
treasure_map_handler = None
