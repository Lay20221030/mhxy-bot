# -*- coding: utf-8 -*-
"""
捉鬼任务处理器

流程：
1. 队长在鬼役NPC处接捉鬼任务
2. 所有号进入鬼谷副本
3. 击败鬼怪（多轮）
4. 完成后返回，继续下一轮

捉鬼通常有6轮，每轮需要击败不同类型的鬼怪
"""

import time
import logging
from typing import List, Optional

from config.settings import COMBAT, NAV

logger = logging.getLogger(__name__)


class GhostHuntHandler:
    """捉鬼任务处理器"""

    def __init__(self, window_group, input_sim, screen_mgr):
        self.wg = window_group
        self.input = input_sim
        self.screen = screen_mgr

    def start_ghost_hunt(self, leader_index: int = 0) -> bool:
        """开始捉鬼（队长接任务）"""
        logger.info("=== 开始捉鬼任务 ===")

        # 队长找到鬼役NPC
        markers = self.screen.wg.detect_quest_markers()
        ghost_markers = [(wi, x, y) for wi, x, y in markers if wi == leader_index]

        if not ghost_markers:
            logger.info("[队长] 未检测到鬼役标记，手动导航")
            # 导航到鬼役NPC位置（西梁女国）
            return False

        # 队长导航到NPC
        _, sx, sy = ghost_markers[0]
        self.input.key("m", leader_index)
        time.sleep(0.3)
        local_x, local_y = self.wg.windows[leader_index].screen_to_local(sx, sy)
        self.input.click(local_x, local_y, leader_index)
        time.sleep(0.3)
        self.input.key("m", leader_index)
        time.sleep(2)

        # 与NPC对话接任务
        if self._check_interactable(leader_index):
            self.input.interact_with_npc(leader_index)
            time.sleep(1)

            # 点击捉鬼确认
            btn = self.screen.find_template("dialog_confirm", leader_index)
            if btn:
                self.input.click(btn[0], btn[1], leader_index)
                time.sleep(2)

        return True

    def enter_ghost_dungeon(self, window_index: int = 0) -> bool:
        """进入鬼谷副本"""
        logger.info(f"[号{window_index+1}] 进入鬼谷副本")

        # 检测组队状态，队长已进入后队员自动进入
        # 检测副本入口
        result = self.screen.find_template("combat_enemy_area", window_index)
        if result:
            # 已经在副本内
            return True

        # 等待队长进入后，队员跟随
        time.sleep(3)
        return False

    def run_ghost_round(self, max_rounds: int = 6) -> bool:
        """运行一轮捉鬼（击败所有鬼怪）"""
        logger.info("--- 开始第1轮捉鬼 ---")

        for round_num in range(1, max_rounds + 1):
            logger.info(f"=== 第 {round_num}/{max_rounds} 轮 ===")

            # 检测战斗
            if self._in_ghost_combat():
                # 战斗由主循环的CombatHandler处理
                break

            time.sleep(1)

        return True

    def _in_ghost_combat(self) -> bool:
        """检测是否在捉鬼战斗中"""
        # 检测战斗UI
        for i in range(len(self.wg.windows)):
            if self.screen.find_template("combat_enemy_area", i):
                return True
        return False

    def check_ghost_round_end(self) -> bool:
        """检测本轮捉鬼是否结束"""
        # 检测奖励/完成对话框
        for i in range(len(self.wg.windows)):
            if self.screen.find_template("dialog_confirm", i):
                return True
        return False

    def confirm_round_end(self):
        """确认本轮结束，进入下一轮"""
        for i in range(len(self.wg.windows)):
            btn = self.screen.find_template("dialog_confirm", i)
            if btn:
                self.input.click(btn[0], btn[1], i)
                time.sleep(1)

    def _check_interactable(self, window_index: int) -> bool:
        """检测是否可交互"""
        region = self.screen.capture_region(window_index, 0, 0,
                                            self.wg.windows[window_index].width, 100)
        yellow = (255, 255, 100)
        lower = [max(0, c - 80) for c in yellow]
        upper = [min(255, c + 80) for c in yellow]
        import cv2
        import numpy as np
        lower_np = np.array(lower, dtype=np.uint8)
        upper_np = np.array(upper, dtype=np.uint8)
        mask = cv2.inRange(region, lower_np, upper_np)
        return cv2.countNonZero(mask) > 50
