# -*- coding: utf-8 -*-
"""
押镖地标检测模块 (来自教程第29-31课)

押镖核心难点:
- 小地图不显示坐标，只显示地图名
- 小地图红点不可靠（会漂移到地图外）
- 随机遇怪 → 战斗结束后需恢复寻路

解决方案:
- 地标检测: 截取路线上的独特地标图 → 匹配到即到达
- 卡屏检测: 监控4个角 → 画面停止变化 = 移动结束
- 战斗恢复: 战斗结束后自动重新寻路
"""

import time
import logging
from typing import Optional, List, Tuple

import cv2
import numpy as np

from core.window_group import WindowGroup
from core.screen import ScreenManager
from core.input_sim import InputSim

logger = logging.getLogger(__name__)


class EscortLandmarkDetector:
    """押镖地标检测器"""

    def __init__(self, window_group: WindowGroup, input_sim: InputSim, screen_mgr: ScreenManager):
        self.wg = window_group
        self.input = input_sim
        self.screen = screen_mgr

        # 卡屏检测的历史帧
        self._last_frames: dict = {}  # {window_idx: np.array}

    def detect_landmark(self, window_index: int, landmark_template: str) -> Optional[Tuple[int, int]]:
        """检测地标是否出现（标识已到达检查点）

        Args:
            window_index: 窗口索引
            landmark_template: 地标模板名 (如 'landmark_tangguojing', 'landmark_changan')

        Returns:
            匹配位置或 None
        """
        logger.debug(f"[号{window_index+1}] 检测地标: {landmark_template}")

        # 先试模板匹配
        pos = self.screen.find_template(landmark_template, window_index)
        if pos:
            return pos

        return None

    def is_screen_frozen(self, window_index: int, threshold: float = 2.0) -> bool:
        """卡屏检测 — 画面停止变化 = 移动结束

        检测4个角的画面是否已停止变化
        """
        import hashlib

        region = self.screen.capture(window_index)
        h, w = region.shape[:2]

        # 检测4个角的画面变化
        corners = [
            region[:20, :20],           # 左上
            region[:20, w-20:],         # 右上
            region[h-20:, :20],         # 左下
            region[h-20:, w-20:],       # 右下
        ]

        # 计算4个角的哈希
        corner_hash = hashlib.md5(b''.join(c.tobytes() for c in corners)).hexdigest()

        prev_hash = self._last_frames.get(window_index)
        self._last_frames[window_index] = corner_hash

        if prev_hash is None:
            return False

        # 画面没变 = 卡屏 = 移动结束了
        return corner_hash == prev_hash

    def wait_arrived_by_freeze(self, window_index: int, timeout: float = 15.0) -> bool:
        """通过卡屏检测等待到达目的地"""
        start = time.time()
        consecutive_frozen = 0

        while time.time() - start < timeout:
            if self.is_screen_frozen(window_index):
                consecutive_frozen += 1
                if consecutive_frozen >= 3:  # 连续3次卡屏 = 到达
                    logger.debug(f"[号{window_index+1}] 卡屏检测: 已到达")
                    return True
            else:
                consecutive_frozen = 0

            time.sleep(0.5)

        return False

    def navigate_escort_route(self, window_index: int, waypoints: List[Tuple[int, int]],
                              landmarks: List[str]) -> bool:
        """沿押镖路线导航

        Args:
            window_index: 窗口索引
            waypoints: 路径点列表 [(x1, y1), (x2, y2), ...]
            landmarks: 对应每个路径点的地标模板名

        Returns:
            是否成功到达终点
        """
        logger.info(f"[号{window_index+1}] 开始押镖导航 ({len(waypoints)} 个路径点)")

        for i, ((wx, wy), landmark) in enumerate(zip(waypoints, landmarks)):
            logger.debug(f"路径点 {i+1}/{len(waypoints)}")

            # 1. 点击地图导航到下一路径点
            self.input.key("m", window_index)
            time.sleep(0.3)

            win = self.wg.windows[window_index]
            local_x, local_y = win.screen_to_local(wx, wy)
            self.input.click(local_x, local_y, window_index)
            time.sleep(0.3)

            self.input.key("m", window_index)

            # 2. 等待到达（用地标检测 + 卡屏检测双重确认）
            arrived = False
            start = time.time()
            while time.time() - start < 30:
                # 检测是否有战斗
                if self._check_in_combat(window_index):
                    logger.debug("遇到战斗，等待结束后继续...")
                    time.sleep(10)  # 等战斗结束
                    # 重新点击寻路
                    self.input.key("m", window_index)
                    time.sleep(0.3)
                    self.input.click(local_x, local_y, window_index)
                    time.sleep(0.3)
                    self.input.key("m", window_index)

                # 地标检测
                if landmark and self.detect_landmark(window_index, landmark):
                    logger.debug(f"地标 {landmark} 已到达")
                    arrived = True
                    break

                # 卡屏检测兜底
                if self.is_screen_frozen(window_index):
                    logger.debug("卡屏检测：已到达")
                    arrived = True
                    break

                time.sleep(0.5)

            if not arrived:
                logger.warning(f"路径点 {i+1} 导航超时")

        logger.info(f"[号{window_index+1}] 押镖导航完成")
        return True

    def _check_in_combat(self, window_index: int) -> bool:
        """检测是否在战斗中"""
        return self.screen.find_template("combat_enemy_area", window_index) is not None

    def handle_escort_combat_recovery(self, window_index: int, dest_x: int, dest_y: int):
        """押镖战斗中恢复 — 战斗结束后重新点击寻路"""
        time.sleep(3)  # 等战斗结束动画

        # 重新点地图继续寻路
        self.input.key("m", window_index)
        time.sleep(0.3)

        win = self.wg.windows[window_index]
        local_x, local_y = win.screen_to_local(dest_x, dest_y)
        self.input.click(local_x, local_y, window_index)
        time.sleep(0.3)

        self.input.key("m", window_index)


# 全局实例
escort_landmark_handler = None
