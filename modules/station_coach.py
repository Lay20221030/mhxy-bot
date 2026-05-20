# -*- coding: utf-8 -*-
"""
驿站/车夫传送模块 (来自教程第13课)

处理游戏中的驿站老板/车夫 NPC:
1. 自动寻路到驿站老板附近
2. 屏蔽商铺/玩家 → 查找移动中的 NPC
3. 点击对话 → 选择目的地 → 传送
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


class StationCoachHandler:
    """驿站车夫处理器"""

    def __init__(self, window_group: WindowGroup, input_sim: InputSim, screen_mgr: ScreenManager):
        self.wg = window_group
        self.input = input_sim
        self.screen = screen_mgr

    def go_to_map_via_coach(self, window_index: int, target_map: str,
                            approach_x: int = 0, approach_y: int = 0) -> bool:
        """通过驿站传送到目标地图

        Args:
            window_index: 窗口索引
            target_map: 目标地图名 (如 '大唐国境')
            approach_x, approach_y: 驿站老板附近的坐标

        Returns:
            传送是否成功
        """
        logger.info(f"[号{window_index+1}] 通过驿站传送至 {target_map}")

        # 1. 如果指定了接近坐标，先导航过去
        if approach_x > 0 and approach_y > 0:
            self.input.key("m", window_index)
            time.sleep(0.5)
            # 点地图传送到接近区域
            win = self.wg.windows[window_index]
            self.input.click(approach_x % win.width, approach_y % win.height, window_index)
            time.sleep(0.5)
            self.input.key("m", window_index)
            time.sleep(1)

        # 2. 等待到达驿站区域
        if not self._check_arrived_near_coach(window_index, timeout=10):
            logger.warning("未到达驿站区域")
            return False

        # 3. 屏蔽干扰元素 (商铺、玩家)
        self._hide_interference(window_index)

        # 4. 查找驿站老板并对话
        if not self._find_and_talk_coach(window_index):
            logger.warning("未找到驿站老板")
            return False

        # 5. 在对话菜单中选目标地图
        if not self._select_target_map(window_index, target_map):
            logger.warning("未找到目标地图选项")
            return False

        # 6. 等待传送完成
        time.sleep(2)
        logger.info(f"已到达 {target_map}")

        return True

    def _check_arrived_near_coach(self, window_index: int, timeout: float = 10) -> bool:
        """检测是否已到达驿站区域（通过小地图颜色特征）"""
        start = time.time()
        while time.time() - start < timeout:
            # 检测屏幕下方是否有交互提示或 NPC 标记
            win = self.wg.windows[window_index]
            region = self.screen.capture_region(window_index, 0, 0, win.width, 100)

            # 检测黄色交互提示
            lower = np.array([150, 150, 50], dtype=np.uint8)
            upper = np.array([255, 255, 150], dtype=np.uint8)
            mask = cv2.inRange(region, lower, upper)

            if cv2.countNonZero(mask) > 50:
                return True

            time.sleep(0.5)

        return False

    def _hide_interference(self, window_index: int):
        """屏蔽商铺和玩家（F9 或游戏内设置）

        梦幻西游支持 F9 键屏蔽玩家显示，减少干扰
        """
        logger.debug(f"[号{window_index+1}] 屏蔽干扰元素")

        # F9 切换玩家显示（按两次确保进入正确状态）
        self.input.key("f9", window_index)
        time.sleep(0.3)
        self.input.key("f9", window_index)
        time.sleep(0.3)

        # 也可以用屏蔽商铺设置（游戏内快捷键）
        # 有些版本是 Alt+Y 或 Ctrl+F

    def _find_and_talk_coach(self, window_index: int,
                             max_retries: int = 3, retry_delay: float = 0.5) -> bool:
        """查找驿站老板并对话

        驿站老板 NPC 会移动，需要：
        1. OpenCV 模板匹配查找
        2. 点击时加偏移（点 NPC 身体下方更稳定）
        3. 重试机制
        """
        # 检查组对话框是否已经打开了
        if self._check_dialog_open(window_index):
            logger.info("驿站对话框已打开，跳过找 NPC")
            return True

        for attempt in range(max_retries):
            # 正面和背面两张图都要匹配
            pos = (self.screen.find_template("coach_front", window_index) or
                   self.screen.find_template("coach_back", window_index))

            if pos:
                # 点击 NPC（稍微偏移到身体中间，避免点到名字区域）
                click_x = pos[0]
                click_y = pos[1] + 30  # 往下偏移

                self.input.click(click_x, click_y, window_index)
                time.sleep(1)

                if self._check_dialog_open(window_index):
                    logger.info(f"[号{window_index+1}] 成功与驿站老板对话")
                    return True

            # 重试等待
            time.sleep(retry_delay)

        return False

    def _check_dialog_open(self, window_index: int) -> bool:
        """检测对话框是否打开"""
        return self.screen.find_template("dialog_confirm", window_index) is not None

    def _select_target_map(self, window_index: int, target_map: str) -> bool:
        """在驿站对话菜单中选目标地图"""
        logger.info(f"[号{window_index+1}] 选择目标地图: {target_map}")

        # 方法1: 模板匹配找 "我要去" 按钮
        pos = self.screen.find_template("dialog_confirm", window_index)
        if pos:
            self.input.click(pos[0], pos[1], window_index)
            time.sleep(0.5)
            return True

        # 方法2: 颜色检测地图名（在对话菜单中找文字颜色）
        pos = self._find_text_in_dialog(window_index, target_map)
        if pos:
            self.input.click(pos[0], pos[1], window_index)
            time.sleep(0.5)
            return True

        return False

    def _find_text_in_dialog(self, window_index: int, text: str) -> Optional[Tuple[int, int]]:
        """在对话菜单中查找指定文字"""
        region = self.screen.capture(window_index)

        # 对话菜单通常在屏幕中下部
        h, w = region.shape[:2]
        dialog_region = region[h//3:2*h//3, w//4:3*w//4]

        # 检测亮色文字区域（对话菜单文字通常是白色/黄色）
        gray = cv2.cvtColor(dialog_region, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x, y, cw, ch = cv2.boundingRect(contour)
            if 30 < cw < 200 and 15 < ch < 40:
                # 返回窗口相对坐标
                global_x = w//4 + x + cw // 2
                global_y = h//3 + y + ch // 2
                return (global_x, global_y)

        return None

    # ─── 综合传送 ────────────────────────────

    def get_available_stations(self) -> List[str]:
        """返回可用的驿站目的地列表"""
        return ["大唐国境", "大唐境外", "长寿村", "傲来国", "建邺城", "宝象国", "西梁女国"]


# 全局实例
station_coach_handler = None
