# -*- coding: utf-8 -*-
"""
师门任务处理器

师门任务类型：
1. 抓宠 - 追逐指定怪物（标记消失 = 抓到）
2. 取物 - 到指定地点拾取物品
3. 打怪 - 击败指定数量怪物
4. 找NPC - 与指定NPC对话

流程：接任务 → 导航 → 完成任务 → 返回交任务
"""

import time
import logging
from typing import Optional, List, Tuple

import cv2
import numpy as np

from config.settings import NAV, COMBAT

logger = logging.getLogger(__name__)


class SectQuestHandler:
    """师门任务处理器"""

    def __init__(self, window_group, input_sim, screen_mgr):
        self.wg = window_group
        self.input = input_sim
        self.screen = screen_mgr

    def accept_quest(self, window_index: int = 0) -> bool:
        """接师门任务（队长用）"""
        markers = self.screen.wg.detect_quest_markers()
        sect_npc_markers = [(wi, x, y) for wi, x, y in markers if wi == window_index]

        if not sect_npc_markers:
            logger.warning(f"[号{window_index+1}] 未检测到师门NPC")
            return False

        # 导航到NPC
        _, sx, sy = sect_npc_markers[0]
        self.input.key("m", window_index)
        time.sleep(0.5)
        local_x, local_y = self.wg.windows[window_index].screen_to_local(sx, sy)
        self.input.click(local_x, local_y, window_index)
        time.sleep(0.5)
        self.input.key("m", window_index)
        time.sleep(1)

        # 与NPC对话接任务
        if self._approach_and_interact(window_index):
            time.sleep(1)
            btn = self.screen.find_template("quest_accept_btn", window_index)
            if btn:
                self.input.click(btn[0], btn[1], window_index)
                logger.info(f"[号{window_index+1}] 已接师门任务")
                return True

        return False

    def complete_quest(self, window_index: int) -> bool:
        """完成当前师门任务"""
        quest_type = self._detect_quest_type(window_index)

        if quest_type == "chase":
            return self._complete_chase(window_index)
        elif quest_type == "fetch":
            return self._complete_fetch(window_index)
        elif quest_type == "kill":
            return self._complete_kill(window_index)
        elif quest_type == "npc":
            return self._complete_npc(window_index)
        else:
            logger.warning(f"[号{window_index+1}] 未知任务类型: {quest_type}")
            return False

    def _detect_quest_type(self, window_index: int, samples: int = 5) -> str:
        """检测任务类型（多次采样提高稳定性）

        通过检测任务标记的颜色和形状来判断：
        - 金色闪烁 + 脚印图标 → 抓宠
        - 黄色 + 地点图标 → 取物/找NPC
        - 红色 + 武器图标 → 打怪

        Args:
            window_index: 窗口索引
            samples: 采样次数
        """
        markers = self.screen.wg.detect_quest_markers()
        quest_markers = [(wi, x, y) for wi, x, y in markers if wi == window_index]

        if not quest_markers:
            return "unknown"

        # 多次采样取多数结果
        type_votes = {"chase": 0, "fetch": 0, "kill": 0, "npc": 0}

        for _ in range(samples):
            _, sx, sy = quest_markers[0]
            win = self.wg.windows[window_index]
            lx, ly = win.screen_to_local(sx, sy)

            # 截取标记周围区域（加一点随机偏移模拟闪烁）
            offset_x = random.randint(-3, 3)
            offset_y = random.randint(-3, 3)
            region = self.screen.capture_region(window_index,
                                                max(0, lx - 15 + offset_x),
                                                max(0, ly - 15 + offset_y), 30, 30)

            # 检测颜色分布
            lower_gold = np.array([150, 120, 50], dtype=np.uint8)
            upper_gold = np.array([255, 200, 100], dtype=np.uint8)
            mask_gold = cv2.inRange(region, lower_gold, upper_gold)
            gold_pixels = cv2.countNonZero(mask_gold)

            lower_red = np.array([0, 50, 50], dtype=np.uint8)
            upper_red = np.array([100, 255, 255], dtype=np.uint8)
            mask_red = cv2.inRange(region, lower_red, upper_red)
            red_pixels = cv2.countNonZero(mask_red)

            # 判断逻辑
            if gold_pixels > 100 and red_pixels < 50:
                type_votes["chase"] += 1
            elif red_pixels > 80:
                type_votes["kill"] += 1
            elif gold_pixels > 50 or red_pixels < 30:
                type_votes["npc"] += 1
            else:
                type_votes["fetch"] += 1

            time.sleep(0.3)

        # 返回投票最多的类型
        best_type = max(type_votes, key=type_votes.get)
        logger.debug(f"[号{window_index+1}] 任务类型投票: {type_votes} → {best_type}")
        return best_type

    def _complete_chase(self, window_index: int) -> bool:
        """完成抓宠任务 - 追逐怪物

        循环：检测标记 → 导航到标记 → 等待标记消失（抓到）→ 继续
        """
        logger.info(f"[号{window_index+1}] 开始抓宠")

        for chase_round in range(15):
            # 获取当前标记位置
            markers_before = self._get_quest_markers(window_index)
            if not markers_before:
                logger.info(f"[号{window_index+1}] 未找到宠物标记，等待...")
                time.sleep(2)
                continue

            _, sx, sy = markers_before[0]
            logger.info(f"[号{window_index+1}] 宠物标记 @ ({sx},{sy})")

            # 导航到宠物位置
            self.input.key("m", window_index)
            time.sleep(0.3)
            local_x, local_y = self.wg.windows[window_index].screen_to_local(sx, sy)
            self.input.click(local_x, local_y, window_index)
            time.sleep(0.3)
            self.input.key("m", window_index)

            # 等待宠物被追上（标记消失）
            if self._wait_marker_disappears(window_index, timeout=20):
                logger.info(f"[号{window_index+1}] 抓到宠物！")
                return True

            logger.info(f"[号{window_index+1}] 未抓到，继续追逐 ({chase_round+1}/15)")

        logger.warning(f"[号{window_index+1}] 抓宠超时")
        return False

    def _wait_marker_disappears(self, window_index: int, timeout: float = 20.0) -> bool:
        """等待任务标记消失（表示已抓到宠物/完成任务）"""
        start = time.time()
        while time.time() - start < timeout:
            markers = self._get_quest_markers(window_index)
            if not markers:
                return True
            time.sleep(1)
        return False

    def _get_quest_markers(self, window_index: int) -> List[Tuple[int, int, int]]:
        """获取指定窗口的任务标记"""
        return [(wi, x, y) for wi, x, y in self.screen.wg.detect_quest_markers()
                if wi == window_index]

    def _complete_fetch(self, window_index: int) -> bool:
        """完成取物任务 - 到指定地点"""
        logger.info(f"[号{window_index+1}] 开始取物")
        self.wg.windows[window_index].has_quest = True
        return self.go_to_location(window_index)

    def _complete_kill(self, window_index: int) -> bool:
        """完成打怪任务 - 击败指定数量怪物"""
        logger.info(f"[号{window_index+1}] 开始打怪")

        if not self.go_to_location(window_index):
            return False

        # 进入战斗后自动战斗
        start = time.time()
        while time.time() - start < 90:
            if self.screen.find_template("combat_enemy_area", window_index):
                # 在战斗中，等待战斗结束
                time.sleep(COMBAT.get("combat_timeout", 120))
                if not self.screen.find_template("combat_enemy_area", window_index):
                    logger.info(f"[号{window_index+1}] 怪物已击败")
                    return True

            time.sleep(1)

        return False

    def _complete_npc(self, window_index: int) -> bool:
        """完成找NPC任务"""
        logger.info(f"[号{window_index+1}] 开始找NPC")
        return self.go_to_location(window_index)

    def go_to_location(self, window_index: int) -> bool:
        """导航到任务地点"""
        markers = self._get_quest_markers(window_index)

        if not markers:
            logger.warning(f"[号{window_index+1}] 未检测到任务标记")
            return False

        _, sx, sy = markers[0]
        self.input.key("m", window_index)
        time.sleep(0.3)
        local_x, local_y = self.wg.windows[window_index].screen_to_local(sx, sy)
        self.input.click(local_x, local_y, window_index)
        time.sleep(0.3)
        self.input.key("m", window_index)

        # 等待到达
        time.sleep(NAV.get("auto_path_wait", 5000) / 1000.0)

        # 交互
        return self._approach_and_interact(window_index)

    def return_to_teacher(self, window_index: int = 0) -> bool:
        """返回师门NPC处交任务"""
        logger.info(f"[号{window_index+1}] 返回师门NPC交任务")

        markers = self._get_quest_markers(window_index)

        if markers:
            _, sx, sy = markers[0]
            self.input.key("m", window_index)
            time.sleep(0.3)
            local_x, local_y = self.wg.windows[window_index].screen_to_local(sx, sy)
            self.input.click(local_x, local_y, window_index)
            time.sleep(0.3)
            self.input.key("m", window_index)
            time.sleep(NAV.get("auto_path_wait", 5000) / 1000.0)

        return self._approach_and_interact(window_index)

    def _approach_and_interact(self, window_index: int) -> bool:
        """接近并交互"""
        time.sleep(1)
        if self._check_interactable(window_index):
            return self.input.interact_with_npc(window_index)
        return False

    def _check_interactable(self, window_index: int) -> bool:
        """检测是否可交互"""
        region = self.screen.capture_region(window_index, 0, 0,
                                            self.wg.windows[window_index].width, 100)
        yellow = (255, 255, 100)
        lower = [max(0, c - 80) for c in yellow]
        upper = [min(255, c + 80) for c in yellow]
        lower_np = np.array(lower, dtype=np.uint8)
        upper_np = np.array(upper, dtype=np.uint8)
        mask = cv2.inRange(region, lower_np, upper_np)
        return cv2.countNonZero(mask) > 50
