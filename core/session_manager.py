# -*- coding: utf-8 -*-
"""
会话管理模块 (来自教程第26+27课)

功能:
1. 游戏掉线检测 — 检测登录界面/掉线弹窗
2. 自动重新登录 — 检测到掉线后自动重登
3. 任务超时检测 — 监控线程，超时则重启任务
4. 自动换号 — 完成一轮后切换到下一个账号
5. 任务链恢复 — 换号后恢复该号的任务配置
"""

import time
import threading
import logging
from typing import Optional, Callable
from enum import Enum

from config.settings import LOOP, COMBAT
from core.window_group import WindowGroup
from core.screen import ScreenManager
from core.input_sim import InputSim

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """会话状态"""
    RUNNING = "running"
    PAUSED = "paused"
    DISCONNECTED = "disconnected"
    LOGIN_SCREEN = "login"
    TIMEOUT = "timeout"
    ERROR = "error"


class SessionManager:
    """会话管理器"""

    def __init__(self, window_group: WindowGroup, input_sim: InputSim, screen_mgr: ScreenManager):
        self.wg = window_group
        self.input = input_sim
        self.screen = screen_mgr

        # 监控线程
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running = False
        self._last_heartbeat = time.time()
        self._timeout_seconds = LOOP.get("stuck_timeout", 60) * 3

        # 账号轮换
        self._current_account_idx = 0
        self._account_task_chain: dict = {}  # 每个账号的任务链配置

    # ─── 掉线检测 ────────────────────────────

    def check_disconnected(self, window_index: int) -> bool:
        """检测指定窗口是否掉线"""
        # 检测登录界面（掉线后通常会回到登录画面）
        if self.screen.find_template("login_screen", window_index):
            return True

        # 检测掉线弹窗
        if self.screen.find_template("disconnect_dialog", window_index):
            return True

        # 检测游戏窗口是否黑屏/无响应（通过连续截图对比）
        region1 = self.screen.capture(window_index)
        time.sleep(1)
        region2 = self.screen.capture(window_index)

        import numpy as np
        diff = np.mean(np.abs(region1.astype(float) - region2.astype(float)))
        if diff < 1:  # 画面几乎不变 = 可能卡死或掉线
            logger.warning(f"[号{window_index+1}] 画面无变化，可能已掉线")
            return True

        return False

    def check_all_disconnected(self) -> dict:
        """检测所有窗口的掉线状态，返回每个窗口的状态"""
        states = {}
        for i in range(len(self.wg.windows)):
            if self.check_disconnected(i):
                states[i] = SessionState.DISCONNECTED
            else:
                states[i] = SessionState.RUNNING
        return states

    # ─── 自动重新登录 ─────────────────────────

    def auto_relogin(self, window_index: int, username: str = "",
                     password: str = "") -> bool:
        """自动重新登录

        Args:
            window_index: 窗口索引
            username: 账号（如果为空则跳过）
            password: 密码

        Returns:
            登录是否成功
        """
        logger.info(f"[号{window_index+1}] 检测到掉线，尝试自动重登...")

        # 1. 确认在登录界面
        if not self.screen.find_template("login_screen", window_index):
            # 不在登录界面，可能是其他问题
            return False

        # 2. 输入账号密码（如果有）
        if username:
            # 点击账号输入框
            win = self.wg.windows[window_index]
            self.input.click(win.width // 2, int(win.height * 0.45), window_index)
            time.sleep(0.5)

            # 输入账号
            for ch in username:
                self.input.key(ch, window_index)
                time.sleep(0.05)
            time.sleep(0.3)

        if password:
            # 点击密码输入框
            win = self.wg.windows[window_index]
            self.input.click(win.width // 2, int(win.height * 0.55), window_index)
            time.sleep(0.5)

            for ch in password:
                self.input.key(ch, window_index)
                time.sleep(0.05)
            time.sleep(0.3)

        # 3. 点击登录按钮
        login_btn = self.screen.find_template("login_button", window_index)
        if login_btn:
            self.input.click(login_btn[0], login_btn[1], window_index)
        else:
            # 兜底：点屏幕中间下方
            win = self.wg.windows[window_index]
            self.input.click(win.width // 2, int(win.height * 0.65), window_index)

        # 4. 等待进入游戏（检测主界面特征）
        time.sleep(3)
        for _ in range(30):  # 最多等30秒
            if self._check_in_game(window_index):
                logger.info(f"[号{window_index+1}] 重新登录成功")
                return True
            time.sleep(1)

        logger.warning(f"[号{window_index+1}] 重新登录超时")
        return False

    def _check_in_game(self, window_index: int) -> bool:
        """检测是否已进入游戏主界面"""
        # 检测小地图/任务栏等主界面元素
        if (self.screen.find_template("quest_npc_flag", window_index) or
                self.screen.find_template("combat_enemy_area", window_index)):
            return True

        # 兜底：检测画面是否有足够的变化（不是纯静态）
        region = self.screen.capture(window_index)
        import numpy as np
        std = np.std(region)
        return std > 30  # 画面有足够变化说明在游戏中

    # ─── 监控线程 ────────────────────────────

    def start_monitor(self, on_timeout: Callable = None):
        """启动监控线程"""
        if self._monitor_running:
            return

        self._monitor_running = True
        self._last_heartbeat = time.time()

        def _monitor_loop():
            while self._monitor_running:
                # 检查是否超时（长时间无心跳）
                elapsed = time.time() - self._last_heartbeat
                if elapsed > self._timeout_seconds:
                    logger.warning(f"任务超时 ({elapsed:.0f}s 无心跳)")
                    if on_timeout:
                        on_timeout()

                # 检查所有窗口是否掉线
                states = self.check_all_disconnected()
                for win_idx, state in states.items():
                    if state == SessionState.DISCONNECTED:
                        logger.warning(f"[号{win_idx+1}] 监控检测到掉线")
                        self.auto_relogin(win_idx)

                time.sleep(5)  # 每5秒检查一次

        self._monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("会话监控线程已启动")

    def heartbeat(self):
        """发送心跳，防止超时"""
        self._last_heartbeat = time.time()

    def stop_monitor(self):
        """停止监控线程"""
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
        logger.info("会话监控线程已停止")

    # ─── 自动换号 ────────────────────────────

    def switch_account(self, from_idx: int, to_idx: int,
                       save_task_chain: bool = True) -> bool:
        """切换到另一个账号

        Args:
            from_idx: 当前窗口
            to_idx: 目标窗口
            save_task_chain: 是否保存当前任务链以便恢复
        """
        if to_idx >= len(self.wg.windows):
            return False

        # 保存当前任务链
        if save_task_chain:
            self._account_task_chain[from_idx] = {
                "last_mode": self.wg.windows[from_idx].has_quest,
                "in_combat": self.wg.windows[from_idx].in_combat,
            }

        # 切换到目标窗口
        self.wg.switch_to(to_idx)
        self._current_account_idx = to_idx

        # 恢复任务
        if to_idx in self._account_task_chain:
            chain = self._account_task_chain[to_idx]
            logger.info(f"[号{to_idx+1}] 恢复任务链: {chain}")

        logger.info(f"已切换到号{to_idx+1}")
        return True

    def rotate_next(self) -> int:
        """轮换到下一个账号"""
        next_idx = (self._current_account_idx + 1) % len(self.wg.windows)
        self.switch_account(self._current_account_idx, next_idx)
        return next_idx

    def get_current_account(self) -> int:
        return self._current_account_idx


# 全局实例
session_manager = None
