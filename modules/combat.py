# -*- coding: utf-8 -*-
"""
战斗处理器 - 多账号协同

回合制战斗逻辑：
1. 检测战斗状态
2. 按顺序给每个号使用技能
3. 检测HP/MP，低时自动吃药
4. 检测战斗结束，进入下一回合
"""

import time
import logging
from typing import Optional, List

import cv2
import numpy as np

from config.settings import COMBAT, KEYS

logger = logging.getLogger(__name__)


class CombatHandler:
    """战斗处理器"""

    def __init__(self, window_group, input_sim, screen_mgr):
        self.wg = window_group
        self.input = input_sim
        self.screen = screen_mgr

    def in_combat(self) -> bool:
        """检测是否处于战斗状态"""
        for i in range(len(self.wg.windows)):
            if self.screen.find_template("combat_enemy_area", i):
                self.wg.windows[i].in_combat = True
                return True
        for win in self.wg.windows:
            win.in_combat = False
        return False

    def get_enemy_count(self, window_index: int = 0) -> int:
        """估算敌方数量"""
        pos = self.screen.find_template("combat_enemy_area", window_index)
        return 1 if pos else 0

    def switch_target(self):
        """切换战斗目标"""
        self.input.switch_target()
        time.sleep(0.3)

    def check_hp_low(self, window_index: int = 0) -> Optional[float]:
        """检测窗口HP百分比

        通过检测左上角红色HP条的像素占比来计算真实百分比
        返回 HP百分比 (0-100)，None表示无法检测
        """
        # HP条通常在角色头像左上方，截取该区域
        win = self.wg.windows[window_index]
        # 截取顶部区域（HP条典型位置）
        bar_x, bar_y = win.x + 20, win.y + 30
        bar_w, bar_h = 150, 20

        region = self.screen.capture_region(window_index, bar_x - win.x, bar_y - win.y, bar_w, bar_h)

        # 红色HP条颜色范围
        lower = np.array([150, 20, 20], dtype=np.uint8)
        upper = np.array([255, 100, 100], dtype=np.uint8)
        mask = cv2.inRange(region, lower, upper)

        # 计算有颜色的像素占比
        total_pixels = bar_w * bar_h
        colored_pixels = cv2.countNonZero(mask)

        if colored_pixels < 10:
            return None  # 没有检测到HP条

        hp_percent = (colored_pixels / total_pixels) * 100
        return round(hp_percent, 1)

    def check_mp_low(self, window_index: int = 0) -> Optional[float]:
        """检测窗口MP百分比

        通过检测蓝色MP条的像素占比来计算真实百分比
        """
        win = self.wg.windows[window_index]
        # MP条通常在HP条下方
        bar_x, bar_y = win.x + 20, win.y + 55
        bar_w, bar_h = 150, 20

        region = self.screen.capture_region(window_index, bar_x - win.x, bar_y - win.y, bar_w, bar_h)

        # 蓝色MP条颜色范围
        lower = np.array([20, 30, 150], dtype=np.uint8)
        upper = np.array([100, 100, 255], dtype=np.uint8)
        mask = cv2.inRange(region, lower, upper)

        total_pixels = bar_w * bar_h
        colored_pixels = cv2.countNonZero(mask)

        if colored_pixels < 10:
            return None

        mp_percent = (colored_pixels / total_pixels) * 100
        return round(mp_percent, 1)

    def use_skill_on_account(self, account_index: int, skill_slot: int):
        """给指定账号使用技能"""
        win = self.wg.windows[account_index]
        logger.debug(f"[号{account_index+1}] 使用技能槽 {skill_slot}")

        self.wg.switch_to(account_index)
        key = KEYS.get(f"skill_{skill_slot}", "f1")
        self.input.key(key, account_index)
        time.sleep(COMBAT.get("skill_interval", 300) / 1000.0)

    def use_potion(self, account_index: int, potion_type: str = "hp"):
        """给指定账号使用药品"""
        if potion_type == "hp":
            self.input.use_hp_potion(account_index)
        else:
            self.input.use_mp_potion(account_index)
        time.sleep(0.5)

    def fight(self, window_group):
        """执行完整战斗流程"""
        logger.info("=== 进入战斗 ===")

        timeout = COMBAT.get("combat_timeout", 120)
        start_time = time.time()
        round_count = 0

        while time.time() - start_time < timeout:
            if self._check_combat_end():
                break

            round_count += 1
            logger.info(f"--- 战斗回合 {round_count} ---")

            # 按顺序给每个号使用技能
            for i in range(len(window_group.windows)):
                if not self._check_combat_end():
                    break

                win = window_group.windows[i]

                # 检查HP/MP，低则吃药
                hp = self.check_hp_low(i)
                if hp is not None and hp < COMBAT.get("hp_potion_threshold", 60):
                    logger.info(f"[号{i+1}] HP过低 ({hp}%)，使用药品")
                    self.use_potion(i, "hp")
                    continue

                mp = self.check_mp_low(i)
                if mp is not None and mp < COMBAT.get("mp_potion_threshold", 40):
                    logger.info(f"[号{i+1}] MP过低 ({mp}%)，使用药品")
                    self.use_potion(i, "mp")
                    continue

                # 使用技能
                rotation = COMBAT.get("skill_rotation", [])
                if rotation:
                    skill_entry = rotation[(i + round_count) % len(rotation)]
                    slot = skill_entry.get("slot", 1)
                    self.use_skill_on_account(i, slot)
                else:
                    self.use_skill_on_account(i, 1)

                time.sleep(COMBAT.get("switch_account_delay", 200) / 1000.0)

            time.sleep(0.5)

        if not self._check_combat_end():
            logger.warning("战斗超时")
        else:
            logger.info("=== 战斗结束 ===")

        self._handle_combat_end()

    def _check_combat_end(self) -> bool:
        """检测战斗是否结束"""
        for i in range(len(self.wg.windows)):
            result = self.screen.find_template("combat_end_dialog", i)
            if result:
                return True
        return False

    def _handle_combat_end(self):
        """处理战斗结束 - 清掉所有对话框"""
        time.sleep(COMBAT.get("combat_end_wait", 2000) / 1000.0)

        for i in range(len(self.wg.windows)):
            # 点击战斗结束对话框
            dialog = self.screen.find_template("combat_end_dialog", i)
            if dialog:
                self.input.click(dialog[0], dialog[1], i)
                time.sleep(1)

            # 循环点击所有确认/奖励按钮（最多5次）
            for _ in range(5):
                btn = self.screen.find_template("dialog_confirm", i)
                if btn:
                    self.input.click(btn[0], btn[1], i)
                    time.sleep(1)
                else:
                    break

        # 清除战斗状态
        for win in self.wg.windows:
            win.in_combat = False
