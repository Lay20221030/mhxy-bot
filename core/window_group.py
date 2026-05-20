# -*- coding: utf-8 -*-
"""
窗口组管理
管理 5 个游戏窗口的截图、输入、状态

每个窗口有独立的屏幕区域 (x, y, w, h)
操作时通过窗口索引路由到正确的区域
"""

import cv2
import numpy as np
import mss
import logging
from typing import Optional, List, Dict, Tuple
from config.settings import ACCOUNT_WINDOWS, SCREEN_RESOLUTION

logger = logging.getLogger(__name__)


class GameWindow:
    """单个游戏窗口"""

    def __init__(self, config: dict, index: int):
        self.index = index
        self.name = config.get("name", f"号{index+1}")
        self.x = config["x"]
        self.y = config["y"]
        self.width = config["width"]
        self.height = config["height"]

        # 状态
        self.in_combat = False
        self.has_quest = False
        self.hp_percent = None
        self.mp_percent = None
        self.is_leader = (index == 0)

    def region(self) -> dict:
        """返回 mss 捕获区域"""
        return {"left": self.x, "top": self.y, "width": self.width, "height": self.height}

    def local_to_screen(self, lx: int, ly: int) -> Tuple[int, int]:
        """局部坐标 → 屏幕绝对坐标"""
        return (lx + self.x, ly + self.y)

    def screen_to_local(self, sx: int, sy: int) -> Tuple[int, int]:
        """屏幕绝对坐标 → 局部坐标"""
        return (sx - self.x, sy - self.y)

    def center(self) -> Tuple[int, int]:
        """窗口中心屏幕坐标"""
        return (self.x + self.width // 2, self.y + self.height // 2)

    def __repr__(self):
        return f"GameWindow({self.name}, {self.width}x{self.height} @ ({self.x},{self.y}))"


class WindowGroup:
    """窗口组 - 管理所有游戏窗口"""

    def __init__(self, window_configs: Optional[List[dict]] = None):
        self.sct = mss.mss()
        self.windows: List[GameWindow] = []

        if window_configs is None:
            window_configs = ACCOUNT_WINDOWS

        for i, cfg in enumerate(window_configs):
            self.windows.append(GameWindow(cfg, i))

        # 当前操作的窗口索引
        self.current_window = 0

        # 模板缓存（按名称 + 分辨率组合缓存）
        self._template_cache: Dict[str, np.ndarray] = {}

    @property
    def leader(self) -> GameWindow:
        """队长窗口"""
        return self.windows[0]

    @property
    def current(self) -> GameWindow:
        """当前窗口"""
        return self.windows[self.current_window]

    def switch_to(self, index: int) -> None:
        """切换到指定窗口"""
        if 0 <= index < len(self.windows):
            self.current_window = index
            logger.debug(f"Switched to window: {self.windows[index].name}")

    def switch_to_next(self) -> None:
        """切换到下一个窗口"""
        self.current_window = (self.current_window + 1) % len(self.windows)

    def switch_to_prev(self) -> None:
        """切换到上一个窗口"""
        self.current_window = (self.current_window - 1) % len(self.windows)

    def capture(self, window_index: Optional[int] = None) -> np.ndarray:
        """截取指定窗口的屏幕"""
        if window_index is None:
            window_index = self.current_window

        win = self.windows[window_index]
        img = self.sct.grab(win.region())
        return cv2.cvtColor(np.array(img), cv2.COLOR_BGRA2BGR)

    def capture_all(self) -> List[np.ndarray]:
        """截取所有窗口"""
        return [self.capture(i) for i in range(len(self.windows))]

    def capture_region(self, window_index: int, x: int, y: int, w: int, h: int) -> np.ndarray:
        """截取指定窗口的局部区域"""
        win = self.windows[window_index]
        region = {
            "left": win.x + x,
            "top": win.y + y,
            "width": w,
            "height": h,
        }
        img = self.sct.grab(region)
        return cv2.cvtColor(np.array(img), cv2.COLOR_BGRA2BGR)

    def _get_cache_key(self, template_name: str, window_index: int) -> str:
        """生成模板缓存键（含分辨率信息）"""
        win = self.windows[window_index]
        return f"{template_name}_{win.width}x{win.height}"

    def find_template(self, template_name: str, window_index: Optional[int] = None,
                      roi: Optional[Tuple[int, int, int, int]] = None) -> Optional[Tuple[int, int]]:
        """
        在指定窗口中查找模板
        返回局部坐标 (x, y)（相对于窗口左上角）

        Args:
            template_name: 模板名称
            window_index: 窗口索引
            roi: 感兴趣区域 (x, y, w, h)，裁剪窗口的一部分来加速匹配
        """
        import time

        if window_index is None:
            window_index = self.current_window

        win = self.windows[window_index]

        # 加载模板（按分辨率缓存）
        cache_key = self._get_cache_key(template_name, window_index)
        if cache_key not in self._template_cache:
            from config.settings import TEMPLATES
            path = TEMPLATES.get(template_name, f"templates/{template_name}.png")
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is None:
                logger.warning(f"Template not found: {template_name} @ {path}")
                return None
            self._template_cache[cache_key] = img

        template = self._template_cache[cache_key]
        th, tw = template.shape[:2]

        # 截取屏幕（支持 ROI）
        if roi:
            screen = self.capture_region(window_index, roi[0], roi[1], roi[2], roi[3])
            # ROI 偏移量（模板匹配结果需加回 ROI 起始坐标）
            roi_offset = (roi[0], roi[1])
        else:
            screen = self.capture(window_index)
            roi_offset = (0, 0)

        # 缩放屏幕加速匹配
        from config.settings import SCREEN_SCALE
        if SCREEN_SCALE < 1.0:
            h, w = screen.shape[:2]
            nw, nh = int(w * SCREEN_SCALE), int(h * SCREEN_SCALE)
            screen = cv2.resize(screen, (nw, nh), interpolation=cv2.INTER_AREA)
            tw_s, th_s = int(tw * SCREEN_SCALE), int(th * SCREEN_SCALE)
            template_s = cv2.resize(template, (tw_s, th_s), interpolation=cv2.INTER_AREA)
            scale = SCREEN_SCALE
        else:
            template_s = template
            tw_s, th_s = tw, th
            scale = 1.0

        result = cv2.matchTemplate(screen, template_s, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        from config.settings import MATCH_THRESHOLD
        if max_val >= MATCH_THRESHOLD:
            # 将匹配位置转换回原始坐标空间
            # max_loc 是 resized 坐标，需要：
            # 1. 加回 ROI 偏移
            # 2. 除以缩放比例还原到原始坐标
            local_x = int((max_loc[0] + roi_offset[0]) / scale)
            local_y = int((max_loc[1] + roi_offset[1]) / scale)
            return (local_x, local_y)

        return None

    def find_all_templates(self, template_name: str) -> List[Tuple[int, int, int]]:
        """在所有窗口中查找模板"""
        results = []
        for i in range(len(self.windows)):
            pos = self.find_template(template_name, i)
            if pos:
                # 转换回屏幕坐标
                sx, sy = self.windows[i].local_to_screen(pos[0], pos[1])
                results.append((i, sx, sy))
        return results

    def detect_quest_markers(self) -> List[Tuple[int, int, int]]:
        """
        检测所有窗口中的任务标记
        返回 [(window_index, screen_x, screen_y), ...]
        """
        results = []
        for i in range(len(self.windows)):
            win = self.windows[i]

            # 在窗口内检测金色/黄色标记
            screen = self.capture(i)
            yellow = (180, 180, 50)
            lower = np.array([max(0, c - 60) for c in yellow])
            upper = np.array([min(255, c + 60) for c in yellow])
            mask = cv2.inRange(screen, lower, upper)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                area = cv2.contourArea(contour)
                if 50 < area < 5000:
                    x, y, w, h = cv2.boundingRect(contour)
                    cx, cy = x + w // 2, y + h // 2
                    sx, sy = win.local_to_screen(cx, cy)
                    results.append((i, sx, sy))

        return results

    def get_status(self) -> Dict:
        """获取所有窗口状态摘要"""
        status = []
        for win in self.windows:
            status.append({
                "index": win.index,
                "name": win.name,
                "in_combat": win.in_combat,
                "has_quest": win.has_quest,
                "is_leader": win.is_leader,
            })
        return status

    def clear_template_cache(self) -> None:
        self._template_cache.clear()
