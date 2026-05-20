# -*- coding: utf-8 -*-
"""
任务读取模块 (来自教程第10课)

从任务面板中提取强盗/贼王等怪物名字
两阶段检测策略：
  阶段1: 大漠/颜色检测（快速）
  阶段2: OpenCV 模板匹配（灵活但慢，兜底）
"""

import time
import logging
from typing import Optional, List, Tuple

import cv2
import numpy as np

from config.settings import TEMPLATES, MATCH_THRESHOLD
from core.window_group import WindowGroup
from core.screen import ScreenManager
from core.input_sim import InputSim

logger = logging.getLogger(__name__)


class TaskReader:
    """任务读取器"""

    def __init__(self, window_group: WindowGroup, input_sim: InputSim, screen_mgr: ScreenManager):
        self.wg = window_group
        self.input = input_sim
        self.screen = screen_mgr

    def read_quest_target(self, window_index: int) -> Optional[dict]:
        """读取当前任务目标（强盗/贼王名字和坐标）

        返回: {"name": "xxx", "map": "xxx", "coords": (x, y)}
        """
        # 1. 打开任务面板
        self.input.key("j", window_index)
        time.sleep(0.5)

        # 2. 两阶段检测任务目标
        target = self._two_stage_detect(window_index)

        # 3. 关闭面板
        self.input.key("esc", window_index)
        time.sleep(0.3)

        return target

    def _two_stage_detect(self, window_index: int) -> Optional[dict]:
        """两阶段检测：先快速颜色 → 失败用 OpenCV

        阶段1: 颜色检测任务面板中的目标文字（快，0.1s）
        阶段2: OpenCV 模板匹配（慢但灵活，兜底）
        """
        # === 阶段1: 颜色检测 ===
        result = self._stage1_color_detect(window_index)
        if result:
            logger.debug(f"[号{window_index+1}] 阶段1命中: {result.get('name', '?')}")
            return result

        # === 阶段2: OpenCV 模板匹配 ===
        logger.debug(f"[号{window_index+1}] 阶段1未命中，走阶段2 OpenCV")
        result = self._stage2_opencv_detect(window_index)
        if result:
            logger.debug(f"[号{window_index+1}] 阶段2命中: {result.get('name', '?')}")

        return result

    def _stage1_color_detect(self, window_index: int) -> Optional[dict]:
        """阶段1：颜色检测任务面板中的文字

        任务面板中的目标文字通常是特定颜色：
        - 金色/黄色 = 当前任务目标
        - 白色 = 普通任务描述
        """
        win = self.wg.windows[window_index]

        # 截取任务面板区域（通常在屏幕中央偏右）
        region = self.screen.capture_region(window_index,
                                            int(win.width * 0.3), 0,
                                            int(win.width * 0.7), win.height)

        # 检测金色/黄色文字（任务目标标记）
        lower = np.array([150, 150, 50], dtype=np.uint8)
        upper = np.array([255, 255, 150], dtype=np.uint8)
        mask = cv2.inRange(region, lower, upper)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            x, y, rw, rh = cv2.boundingRect(contour)
            # 筛选合理大小的文字区域
            if 100 < area < 3000 and 10 < rh < 30:
                # 找到了任务目标标记
                return {"name": "quest_target_detected", "pos": (x + rw // 2, y + rh // 2),
                        "method": "color"}

        return None

    def _stage2_opencv_detect(self, window_index: int) -> Optional[dict]:
        """阶段2：OpenCV 模板匹配任务面板中的目标"""
        # 尝试找任务面板中的目标标记
        for template_name in ["quest_target_marker", "quest_npc_flag"]:
            pos = self.screen.find_template(template_name, window_index)
            if pos:
                return {"name": template_name, "pos": pos, "method": "opencv"}

        return None

    def find_monster_in_field(self, window_index: int, monster_name: str) -> Optional[Tuple[int, int]]:
        """在野外找指定怪物

        策略：
        1. 先用任务标记颜色（金色）快速定位候选区域
        2. 再对候选区域做 OpenCV 模板匹配确认
        """
        win = self.wg.windows[window_index]

        # 阶段1：颜色检测金色任务标记
        region = self.screen.capture(window_index)

        lower = np.array([150, 150, 50], dtype=np.uint8)
        upper = np.array([255, 255, 150], dtype=np.uint8)
        mask = cv2.inRange(region, lower, upper)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 50 < area < 5000:
                x, y, w, h = cv2.boundingRect(contour)
                candidates.append((x + w // 2, y + h // 2))

        # 阶段2：如果候选太多/太少，用 OpenCV 模板
        if len(candidates) == 1:
            return candidates[0]
        elif len(candidates) > 1:
            # 多个候选，用模板匹配确认
            pos = self.screen.find_template("quest_npc_flag", window_index)
            if pos:
                # 找离模板匹配最近的候选
                return min(candidates,
                          key=lambda c: (c[0] - pos[0])**2 + (c[1] - pos[1])**2)

        # 兜底：直接模板匹配
        return self.screen.find_template("quest_npc_flag", window_index)

    def read_bandit_name(self, window_index: int) -> Optional[str]:
        """从任务面板读取强盗名字"""
        target = self.read_quest_target(window_index)
        if target:
            return f"bandit_{target.get('pos', (0, 0))}"
        return None

    def detect_monster_name_color(self, window_index: int,
                                  color_hex: str = "ff0000") -> Optional[Tuple[int, int]]:
        """通过颜色检测怪物名字（红色名字=可攻击目标）

        梦幻西游中，可攻击怪物名字通常是红色
        """
        region = self.screen.capture(window_index)

        if color_hex == "ff0000":  # 红色
            lower = np.array([0, 0, 180], dtype=np.uint8)
            upper = np.array([80, 80, 255], dtype=np.uint8)

        mask = cv2.inRange(region, lower, upper)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            x, y, rw, rh = cv2.boundingRect(contour)
            # 怪物名字通常是细长文字
            if 50 < area < 2000 and rw > rh * 2:
                return (x + rw // 2, y + rh // 2)

        return None


# 全局实例
task_reader_handler = None
