# -*- coding: utf-8 -*-
"""
验证码处理模块

NetEase 游戏常见验证码类型：
1. 登录验证码 - 弹窗确认
2. 滑动拼图 - 拖动滑块到缺口位置
3. 图形选择 - 点击图中指定元素

策略：
- 检测验证码出现 → 暂停主循环
- 尝试自动点击确认按钮
- 滑动拼图：检测缺口位置 + 模拟滑动
- 超时或失败 → 人工处理
"""

import time
import random
import logging
from typing import Optional, Tuple
from enum import Enum

import cv2
import numpy as np
import pyautogui

logger = logging.getLogger(__name__)


class CaptchaType(Enum):
    """验证码类型"""
    DIALOG = "dialog"           # 简单对话框
    SLIDER = "slider"           # 滑动拼图
    IMAGE_SELECT = "image_select"  # 图形选择


class CaptchaHandler:
    """验证码处理器"""

    def __init__(self, window_group, input_sim, screen_mgr):
        self.wg = window_group
        self.input = input_sim
        self.screen = screen_mgr

    def detect_captcha(self) -> Optional[CaptchaType]:
        """检测是否有验证码出现

        返回验证码类型，无验证码返回 None
        """
        # 1. 检测对话框型验证码
        if self._detect_dialog_captcha():
            return CaptchaType.DIALOG

        # 2. 检测滑动拼图
        if self._detect_slider_captcha():
            return CaptchaType.SLIDER

        # 3. 检测图形选择
        if self._detect_image_select_captcha():
            return CaptchaType.IMAGE_SELECT

        return None

    def _detect_dialog_captcha(self) -> bool:
        """检测简单对话框验证码"""
        # 检测屏幕中央的对话框区域
        for i in range(len(self.wg.windows)):
            result = self.screen.find_template("captcha_dialog", i)
            if result:
                logger.info(f"检测到对话框验证码 (窗口{i})")
                return True

            # 备用：检测白色/灰色对话框区域
            region = self.screen.capture_region(i, 0, 0,
                                                self.wg.windows[i].width,
                                                self.wg.windows[i].height)
            # 检测大面积白色区域（对话框特征）
            lower = np.array([200, 200, 200], dtype=np.uint8)
            upper = np.array([255, 255, 255], dtype=np.uint8)
            mask = cv2.inRange(region, lower, upper)

            # 如果中心区域有大面积白色，可能是对话框
            h, w = mask.shape
            center_region = mask[h//3:2*h//3, w//3:2*w//3]
            white_pixels = cv2.countNonZero(center_region)
            if white_pixels > (h * w // 9) * 0.5:
                logger.info(f"检测到对话框区域 (窗口{i})")
                return True

        return False

    def _detect_slider_captcha(self) -> bool:
        """检测滑动拼图验证码"""
        # 滑动拼图通常有：滑块轨道、滑块、缺口
        for i in range(len(self.wg.windows)):
            # 检测底部滑块轨道（水平长条）
            bottom = self.screen.capture_region(i, 0,
                                                self.wg.windows[i].height - 150,
                                                self.wg.windows[i].width, 150)
            # 滑块轨道通常是灰色长条
            lower = np.array([150, 150, 150], dtype=np.uint8)
            upper = np.array([220, 220, 220], dtype=np.uint8)
            mask = cv2.inRange(bottom, lower, upper)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                # 滑块轨道特征：宽而扁
                if w > 200 and h < 50:
                    logger.info(f"检测到滑动拼图 (窗口{i})")
                    return True

        return False

    def _detect_image_select_captcha(self) -> bool:
        """检测图形选择验证码"""
        # 图形选择通常有多个小图格
        for i in range(len(self.wg.windows)):
            region = self.screen.capture_region(i, 0, 100,
                                                self.wg.windows[i].width, 300)
            # 检测网格状排列的图块
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # 统计图块数量
            block_count = sum(1 for c in contours if 500 < cv2.contourArea(c) < 50000)
            if block_count >= 4:  # 至少4个图块（2x2网格）
                logger.info(f"检测到图形选择验证码 (窗口{i})")
                return True

        return False

    def handle_captcha(self, captcha_type: CaptchaType) -> bool:
        """处理验证码"""
        logger.info(f"开始处理验证码: {captcha_type.value}")

        if captcha_type == CaptchaType.DIALOG:
            return self._handle_dialog()
        elif captcha_type == CaptchaType.SLIDER:
            return self._handle_slider()
        elif captcha_type == CaptchaType.IMAGE_SELECT:
            return self._handle_image_select()

        return False

    def _handle_dialog(self) -> bool:
        """处理对话框验证码 - 点击确认按钮"""
        logger.info("点击对话框确认按钮")

        for i in range(len(self.wg.windows)):
            btn = self.screen.find_template("dialog_confirm", i)
            if btn:
                self.input.click(btn[0], btn[1], i)
                time.sleep(1)
                return True

        # 备用：点击屏幕下方中央
        win = self.wg.leader
        self.input.click(win.width // 2, int(win.height * 0.85), 0)
        time.sleep(1)
        return True

    def _handle_slider(self) -> bool:
        """处理滑动拼图验证码"""
        logger.info("处理滑动拼图")

        for i in range(len(self.wg.windows)):
            # 找到滑块位置
            slider_pos = self._find_slider(i)
            if slider_pos:
                # 找到缺口位置
                gap_pos = self._find_gap(i)
                if gap_pos:
                    # 计算滑动距离
                    distance = abs(gap_pos[0] - slider_pos[0])
                    logger.info(f"滑动距离: {distance}px")

                    # 模拟滑动（带随机抖动）
                    self._slide_with_jitter(i, distance)
                    time.sleep(1)
                    return True

        logger.warning("滑动拼图处理失败")
        return False

    def _find_slider(self, window_index: int) -> Optional[Tuple[int, int]]:
        """找到滑块位置"""
        region = self.screen.capture_region(window_index, 0,
                                            self.wg.windows[window_index].height - 150,
                                            self.wg.windows[window_index].width, 150)

        # 滑块通常是圆形或方形，颜色较深
        lower = np.array([80, 80, 80], dtype=np.uint8)
        upper = np.array([180, 180, 180], dtype=np.uint8)
        mask = cv2.inRange(region, lower, upper)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if 500 < area < 10000:
                x, y, w, h = cv2.boundingRect(contour)
                return (x + w // 2, y + h // 2)

        return None

    def _find_gap(self, window_index: int) -> Optional[Tuple[int, int]]:
        """找到缺口位置"""
        region = self.screen.capture_region(window_index, 0,
                                            self.wg.windows[window_index].height - 150,
                                            self.wg.windows[window_index].width, 150)

        # 缺口通常是深色区域
        lower = np.array([30, 30, 30], dtype=np.uint8)
        upper = np.array([100, 100, 100], dtype=np.uint8)
        mask = cv2.inRange(region, lower, upper)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if 200 < area < 5000:
                x, y, w, h = cv2.boundingRect(contour)
                return (x + w // 2, y + h // 2)

        return None

    def _slide_with_jitter(self, window_index: int, distance: float):
        """模拟带随机抖动的滑动"""
        win = self.wg.windows[window_index]

        # 起始位置（滑块中心）
        start_x = win.x + 50
        start_y = win.y + win.height - 100

        # 目标位置
        end_x = start_x + distance
        end_y = start_y

        # 使用 pyautogui drag 模拟滑动
        pyautogui.moveTo(start_x, start_y)
        time.sleep(0.1)

        # 带抖动的滑动轨迹
        steps = max(5, int(distance / 20))
        for step in range(1, steps + 1):
            t = step / steps
            jitter_x = random.randint(-3, 3)
            jitter_y = random.randint(-2, 2)
            current_x = start_x + (end_x - start_x) * t + jitter_x
            current_y = start_y + (end_y - start_y) * t + jitter_y

            pyautogui.dragTo(int(current_x), int(current_y), duration=0.02)
            time.sleep(0.01)

    def _handle_image_select(self) -> bool:
        """处理图形选择验证码"""
        logger.info("处理图形选择")

        for i in range(len(self.wg.windows)):
            # 点击第一个图块作为示例
            win = self.wg.windows[i]
            self.input.click(50, 150, i)
            time.sleep(1)

            # 点击确认
            btn = self.screen.find_template("dialog_confirm", i)
            if btn:
                self.input.click(btn[0], btn[1], i)
                time.sleep(1)
                return True

        logger.warning("图形选择验证码处理失败")
        return False

    def handle_captcha_with_retry(self, max_retries: int = 3) -> bool:
        """带重试的验证码处理"""
        for attempt in range(max_retries):
            captcha_type = self.detect_captcha()
            if captcha_type:
                logger.info(f"尝试 {attempt+1}/{max_retries} 处理验证码")
                if self.handle_captcha(captcha_type):
                    logger.info("验证码处理成功")
                    return True

            time.sleep(1)

        logger.warning(f"验证码处理失败，已重试 {max_retries} 次")
        return False
