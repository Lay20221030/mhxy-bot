# -*- coding: utf-8 -*-
"""
输入模拟 - 多窗口支持
鼠标点击路由到指定窗口区域
键盘输入需要切换焦点到目标窗口
"""

import pyautogui
import time
import random
import logging
from typing import Optional
from config.settings import COMMON

logger = logging.getLogger(__name__)


def _rand_delay():
    d = random.randint(
        COMMON.get("random_delay_min", 100),
        COMMON.get("random_delay_max", 400)
    ) / 1000.0
    time.sleep(d)


class InputSim:
    """输入模拟器 - 依赖 WindowGroup"""

    def __init__(self, window_group):
        self.wg = window_group
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05

    def _focus_window(self, window_index: int) -> bool:
        """将焦点切换到指定窗口（通过点击窗口内任意位置）"""
        win = self.wg.windows[window_index]
        # 点击窗口左上角附近（避免点到游戏内UI）
        px, py = win.x + 10, win.y + 10
        try:
            pyautogui.click(px, py)
            time.sleep(0.15)
            return True
        except Exception as e:
            logger.error(f"Focus window {window_index} failed: {e}")
            return False

    def click(self, x: int, y: int, window_index: Optional[int] = None) -> bool:
        """点击 - 坐标为窗口局部坐标"""
        if window_index is None:
            window_index = self.wg.current_window

        win = self.wg.windows[window_index]
        sx, sy = win.local_to_screen(x, y)

        try:
            pyautogui.click(sx, sy)
            _rand_delay()
            return True
        except Exception as e:
            logger.error(f"Click ({x},{y}) in window {window_index} failed: {e}")
            return False

    def double_click(self, x: int, y: int, window_index: Optional[int] = None) -> bool:
        if window_index is None:
            window_index = self.wg.current_window
        win = self.wg.windows[window_index]
        sx, sy = win.local_to_screen(x, y)
        try:
            pyautogui.doubleClick(sx, sy)
            _rand_delay()
            return True
        except Exception as e:
            logger.error(f"Double-click failed: {e}")
            return False

    def key(self, key: str, window_index: Optional[int] = None) -> bool:
        """按键 - 需要切换焦点到目标窗口"""
        if window_index is None:
            window_index = self.wg.current_window

        # 切换到目标窗口
        if window_index != self.wg.current_window:
            self._focus_window(window_index)

        try:
            pyautogui.press(key)
            time.sleep(COMMON.get("key_delay", 150) / 1000.0)
            return True
        except Exception as e:
            logger.error(f"Key '{key}' in window {window_index} failed: {e}")
            return False

    def hotkey(self, *keys: str, window_index: Optional[int] = None) -> bool:
        if window_index is None:
            window_index = self.wg.current_window

        if window_index != self.wg.current_window:
            self._focus_window(window_index)

        try:
            pyautogui.hotkey(*keys)
            time.sleep(COMMON.get("key_delay", 150) / 1000.0)
            return True
        except Exception as e:
            logger.error(f"Hotkey {keys} failed: {e}")
            return False

    def wait(self, seconds: float) -> None:
        time.sleep(seconds)

    # ─── 梦幻西游专用操作 ──────────────────────

    def interact_with_npc(self, window_index: Optional[int] = None):
        """与NPC交互"""
        logger.info(f"[{self.wg.current.name}] Interacting with NPC...")
        return self.key("space", window_index)

    def open_map(self, window_index: Optional[int] = None):
        """打开地图"""
        logger.info(f"[{self.wg.current.name}] Opening map...")
        return self.key("m", window_index)

    def open_quest_panel(self, window_index: Optional[int] = None):
        """打开任务面板"""
        logger.info(f"[{self.wg.current.name}] Opening quest panel...")
        return self.key("j", window_index)

    def toggle_auto_combat(self, window_index: Optional[int] = None):
        """开关自动战斗"""
        logger.info(f"[{self.wg.current.name}] Toggling auto combat...")
        return self.key("f9", window_index)

    def use_skill(self, slot: int, window_index: Optional[int] = None):
        """使用技能槽"""
        from config.settings import KEYS
        key = KEYS.get(f"skill_{slot}", "f1")
        logger.debug(f"[{self.wg.current.name}] Using skill slot {slot}: {key}")
        return self.key(key, window_index)

    def use_hp_potion(self, window_index: Optional[int] = None):
        return self.key("f6", window_index)

    def use_mp_potion(self, window_index: Optional[int] = None):
        return self.key("f7", window_index)

    def switch_target(self, window_index: Optional[int] = None):
        return self.key("tab", window_index)

    def esc(self, count: int = 2, window_index: Optional[int] = None):
        if window_index is not None:
            self._focus_window(window_index)
        for _ in range(count):
            self.key("escape")

    def click_dialog_button(self, button_type: str = "continue", window_index: Optional[int] = None):
        """点击对话框按钮"""
        if window_index is None:
            window_index = self.wg.current_window

        win = self.wg.windows[window_index]
        gw, gh = win.width, win.height

        # 对话框按钮在屏幕下方中央
        btn_x = gw // 2
        btn_y = int(gh * 0.85)

        return self.click(btn_x, btn_y, window_index)
