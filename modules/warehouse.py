# -*- coding: utf-8 -*-
"""
仓库管理模块 (来自教程第32-33课)

功能:
1. 自动飞到长安天台仓库
2. 找到仓库管理员 → 右键打开仓库
3. 取出藏宝图/物品
4. 通过好友列表转图给其他号
"""

import time
import logging
from typing import Optional, List, Tuple

from core.window_group import WindowGroup
from core.screen import ScreenManager
from core.input_sim import InputSim

logger = logging.getLogger(__name__)


class WarehouseHandler:
    """仓库处理器"""

    # 长安天台仓库管理员的游戏坐标
    WAREHOUSE_COORDS = (347, 243)

    def __init__(self, window_group: WindowGroup, input_sim: InputSim, screen_mgr: ScreenManager):
        self.wg = window_group
        self.input = input_sim
        self.screen = screen_mgr

    def go_to_warehouse(self, window_index: int) -> bool:
        """飞到长安天台仓库"""
        logger.info(f"[号{window_index+1}] 前往长安天台仓库")

        # 1. 用飞行符飞长安
        self.input.key("i", window_index)
        time.sleep(0.5)

        # 找飞行符使用
        scroll_pos = self.screen.find_template("fly_scroll_icon", window_index)
        if scroll_pos:
            self.input.click(scroll_pos[0], scroll_pos[1], window_index)
            time.sleep(0.8)
            # 选长安
            self.input.click(100, 200, window_index)
            time.sleep(0.5)

        self.input.key("esc", window_index)
        time.sleep(1)

        # 2. 移动到仓库管理员位置
        win = self.wg.windows[window_index]
        wx, wy = self.WAREHOUSE_COORDS
        self.input.key("m", window_index)
        time.sleep(0.3)

        local_x, local_y = win.screen_to_local(wx, wy)
        self.input.click(local_x, local_y, window_index)
        time.sleep(0.3)

        self.input.key("m", window_index)
        time.sleep(2)

        return True

    def open_warehouse(self, window_index: int) -> bool:
        """打开仓库"""
        # 找仓库管理员 NPC
        npc_pos = (self.screen.find_template("warehouse_npc", window_index) or
                   self.screen.find_template("dialog_confirm", window_index))

        if npc_pos:
            # 右键打开仓库
            import pyautogui
            win = self.wg.windows[window_index]
            sx, sy = win.local_to_screen(npc_pos[0], npc_pos[1])
            pyautogui.rightClick(sx, sy)
            time.sleep(1)
            return True

        return False

    def withdraw_maps(self, window_index: int, count: int = 20) -> int:
        """从仓库取出藏宝图

        Args:
            window_index: 窗口索引
            count: 要取出的数量

        Returns:
            实际取出的数量
        """
        logger.info(f"[号{window_index+1}] 从仓库取图 ({count}张)")

        withdrawn = 0
        for _ in range(count):
            # 找藏宝图图标
            map_icon = self.screen.find_template("treasure_map_icon", window_index)
            if not map_icon:
                logger.debug("仓库无更多藏宝图")
                break

            # 右键取出
            import pyautogui
            win = self.wg.windows[window_index]
            sx, sy = win.local_to_screen(map_icon[0], map_icon[1])
            pyautogui.rightClick(sx, sy)
            time.sleep(0.3)

            # 点击"取出"选项
            btn = self.screen.find_template("dialog_confirm", window_index)
            if btn:
                self.input.click(btn[0], btn[1], window_index)
                time.sleep(0.3)

            withdrawn += 1

        logger.info(f"已取出 {withdrawn} 张藏宝图")
        return withdrawn

    def transfer_maps_to_alt(self, from_window: int, to_window: int,
                            count: int = 20) -> bool:
        """将藏宝图转给另一个号

        通过好友列表 → ALT+点击给予

        Args:
            from_window: 源窗口
            to_window: 目标窗口
            count: 转移数量
        """
        logger.info(f"[号{from_window+1}] 转图 → 号{to_window+1}")

        # 1. 打开好友列表
        self.input.key("alt+f", from_window)
        time.sleep(0.5)

        # 2. 找到好友分组（预先把仓库号放在固定分组里）
        friend_pos = self.screen.find_template("friend_icon", from_window)
        if friend_pos:
            self.input.click(friend_pos[0], friend_pos[1], from_window)
            time.sleep(0.5)

        # 3. 打开背包，ALT+点击物品给予
        self.input.key("i", from_window)
        time.sleep(0.5)

        transferred = 0
        for _ in range(count):
            map_icon = self.screen.find_template("treasure_map_icon", from_window)
            if not map_icon:
                break

            # ALT + 点击 = 给予
            import pyautogui
            win = self.wg.windows[from_window]
            sx, sy = win.local_to_screen(map_icon[0], map_icon[1])

            pyautogui.keyDown("alt")
            time.sleep(0.05)
            pyautogui.click(sx, sy)
            time.sleep(0.05)
            pyautogui.keyUp("alt")

            # 确认给予
            time.sleep(0.3)
            btn = self.screen.find_template("dialog_confirm", from_window)
            if btn:
                self.input.click(btn[0], btn[1], from_window)

            transferred += 1

        # 4. 关闭界面
        self.input.key("esc", from_window)
        time.sleep(0.3)

        logger.info(f"已转 {transferred} 张图")
        return transferred > 0

    def auto_withdraw_and_transfer(self, from_window: int, to_window: int,
                                   map_count: int = 20) -> bool:
        """一键取图+转图"""
        if not self.go_to_warehouse(from_window):
            return False

        if not self.open_warehouse(from_window):
            return False

        withdrawn = self.withdraw_maps(from_window, map_count)
        if withdrawn == 0:
            return False

        return self.transfer_maps_to_alt(from_window, to_window, withdrawn)


# 全局实例
warehouse_handler = None
