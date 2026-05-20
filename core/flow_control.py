# -*- coding: utf-8 -*-
"""
流控模块 - 防检测/防封

模拟人类操作行为，降低被网易反作弊系统检测的风险：
1. 滑动任务 - 滑动过程中随机暂停
2. 判断次数 - 连续操作不超过上限
3. 随机延迟 - 不同操作有不同延迟范围
4. 操作间隔 - 控制每分钟操作次数
"""

import time
import random
import logging
from collections import deque
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class FlowControl:
    """流控制器"""

    def __init__(self, max_ops_per_minute: int = 60):
        """
        Args:
            max_ops_per_minute: 每分钟最大操作次数
        """
        self.max_ops_per_minute = max_ops_per_minute
        # 操作时间戳队列（保留最近60秒的操作）
        self._ops: deque = deque()
        # 滑动暂停概率
        self._slide_pause_prob = 0.15

    def record_op(self):
        """记录一次操作"""
        now = time.time()
        self._ops.append(now)
        # 清理超过60秒的旧记录
        while self._ops and self._ops[0] < now - 60:
            self._ops.popleft()

    def check_count(self) -> bool:
        """判断次数 - 返回是否超过上限"""
        now = time.time()
        recent = sum(1 for t in self._ops if t > now - 60)
        return recent >= self.max_ops_per_minute

    def wait_if_needed(self):
        """如果接近上限则等待"""
        if self.check_count():
            wait_time = 60 - (time.time() - self._ops[0])
            if wait_time > 0:
                logger.debug(f"操作次数达到上限，等待 {wait_time:.1f}s")
                time.sleep(wait_time)

    def random_delay(self, min_ms: int = 100, max_ms: int = 500) -> float:
        """随机延迟（毫秒），返回实际延迟时间"""
        delay = random.uniform(min_ms, max_ms) / 1000.0
        time.sleep(delay)
        return delay

    def slide_pause(self) -> bool:
        """滑动任务 - 模拟滑动过程中的随机暂停"""
        if random.random() < self._slide_pause_prob:
            pause_time = random.uniform(0.2, 0.8)
            time.sleep(pause_time)
            logger.debug(f"滑动暂停 {pause_time:.2f}s")
            return True
        return False

    def human_like_delay(self, base_ms: int = 300) -> float:
        """模拟人类操作延迟（带随机性和抖动）"""
        # 基础延迟 + 随机抖动（-30% ~ +50%）
        jitter = random.uniform(-0.3, 0.5)
        delay = base_ms * (1 + jitter) / 1000.0
        time.sleep(delay)
        return delay

    def before(self, func: Callable) -> bool:
        """在执行前检查流控条件"""
        if self.check_count():
            logger.debug("操作次数超限，等待...")
            self.wait_if_needed()
        return True

    def uncheck(self, func: Callable) -> bool:
        """取消检查 - 跳过流控检查"""
        return True


def sliding_task(func: Callable) -> bool:
    """装饰器：滑动任务"""
    fc = FlowControl()
    fc.slide_pause()
    return func()


def check_count_task(func: Callable) -> bool:
    """装饰器：判断次数"""
    fc = FlowControl()
    if fc.check_count():
        fc.wait_if_needed()
    return func()


# 全局流控实例
flow_control = FlowControl()
