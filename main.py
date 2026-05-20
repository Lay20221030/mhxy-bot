# -*- coding: utf-8 -*-
"""
梦幻西游自动脚本 - 多账号主控版

管理5个游戏窗口，协调队长/队员任务、战斗、导航
支持：师门任务、捉鬼任务、押镖、副本、主线
"""

import sys
import time
import logging
import keyboard
from datetime import datetime

from config.settings import LOOP, COMBAT, COMMON
from core.window_group import WindowGroup
from core.screen import ScreenManager
from core.input_sim import InputSim
from modules.combat import CombatHandler
from modules.navigation import Navigator
from modules.tasks.sect_quest import SectQuestHandler
from modules.tasks.ghost_hunt import GhostHuntHandler
from modules.tasks.treasure_map import TreasureMapHandler
from core.captcha import CaptchaHandler, CaptchaType
from core.flow_control import FlowControl

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/mhxy_bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


class AutoBot:
    """全自动脚本主类"""

    def __init__(self, enable_ui: bool = False):
        # 初始化窗口组
        self.wg = WindowGroup()
        logger.info(f"已加载 {len(self.wg.windows)} 个窗口")
        for win in self.wg.windows:
            logger.info(f"  {win.name}: @({win.x},{win.y}) {win.width}x{win.height}")

        # 初始化子系统（都依赖 WindowGroup）
        self.screen = ScreenManager(self.wg)
        self.input = InputSim(self.wg)
        self.combat = CombatHandler(self.wg, self.input, self.screen)
        self.navigator = Navigator(self.wg, self.input, self.screen)
        self.sect_quest = SectQuestHandler(self.wg, self.input, self.screen)
        self.ghost_hunt = GhostHuntHandler(self.wg, self.input, self.screen)
        self.captcha_handler = CaptchaHandler(self.wg, self.input, self.screen)
        self.treasure_map = TreasureMapHandler(self.wg, self.input, self.screen)

        # 流控（防检测）
        self.flow_control = FlowControl(max_ops_per_minute=60)

        # 运行状态
        self.paused = False
        self.running = True
        self.current_mode = "idle"

        # 防卡死检测
        self.last_activity = time.time()
        self.stuck_count = 0

        # 注册全局热键（用 pyautogui 兼容，避免与游戏按键冲突）
        keyboard.on_press_key(LOOP.get("hotkey_pause", "f12"), self._on_pause)
        keyboard.on_press_key(LOOP.get("hotkey_exit", "f11"), self._on_exit)

        # UI 面板
        self.ui = None
        if enable_ui:
            try:
                from ui import MainWindow
                self.ui = MainWindow(self)
            except ImportError:
                logger.info("PyQt5 未安装，跳过 UI 面板")

    def _record_activity(self):
        """记录活动，用于防卡死检测"""
        self.last_activity = time.time()
        self.flow_control.record_op()

    def _on_pause(self, e):
        self.paused = not self.paused
        logger.info(f"[{'PAUSED' if self.paused else 'RESUMED'}]")

    def _on_exit(self, e):
        logger.info("退出热键触发，准备退出...")
        self.running = False

    def run(self, mode: str = "quest", enable_ui: bool = False):
        """启动主循环"""
        self.current_mode = mode
        logger.info(f"=== 启动自动脚本，模式: {mode} ===")

        # 启动 UI
        if enable_ui and self.ui is None:
            try:
                from ui import MainWindow
                self.ui = MainWindow(self)
                self.ui.show()
            except ImportError:
                pass

        try:
            while self.running:
                if self.paused:
                    time.sleep(0.5)
                    continue

                # 1. 验证码检测（最高优先级）
                if self._check_captcha():
                    continue

                # 2. 防卡死检测
                if LOOP.get("stuck_detection", False):
                    self._check_stuck()

                # 3. 检测死亡（高优先级）
                if self._check_death():
                    self._handle_death()
                    continue

                # 4. 流控：接近上限时等待
                self.flow_control.wait_if_needed()

                # 5. 根据模式分发
                getattr(self, f"_loop_{mode}")()

        except KeyboardInterrupt:
            logger.info("收到中断信号")
        finally:
            logger.info("脚本已退出")

    def _check_stuck(self):
        """检测是否卡住（长时间无活动）"""
        stuck_timeout = LOOP.get("stuck_timeout", 60)
        elapsed = time.time() - self.last_activity

        if elapsed > stuck_timeout:
            self.stuck_count += 1
            logger.warning(f"卡住检测 ({self.stuck_count}/3) - {elapsed:.0f}s 无活动")

            if self.stuck_count >= 3:
                logger.warning("连续卡住，尝试恢复...")
                self._recover_from_stuck()
                self.stuck_count = 0
        else:
            self.stuck_count = max(0, self.stuck_count - 1)

    def _recover_from_stuck(self):
        """从卡住状态恢复"""
        logger.info("执行恢复操作：按ESC关闭弹窗 → 重新检测")
        self.input.esc(count=2)
        time.sleep(1)

    def _check_captcha(self) -> bool:
        """检测并处理验证码，返回是否已处理"""
        captcha_type = self.captcha_handler.detect_captcha()
        if captcha_type:
            logger.info(f"检测到验证码: {captcha_type.value}")
            # 暂停主循环处理验证码
            self.paused = True
            if self.captcha_handler.handle_captcha_with_retry():
                logger.info("验证码处理成功，恢复运行")
                self.paused = False
                return True
            else:
                logger.warning("验证码处理失败，等待手动处理")
                return True
        return False

    # ─── 死亡检测与处理 ──────────────────────

    def _check_death(self) -> bool:
        """检测是否有窗口处于死亡状态"""
        for i in range(len(self.wg.windows)):
            result = self.screen.find_template("death_dialog", i)
            if result:
                logger.warning(f"窗口 {i} 检测到死亡对话框")
                return True
        return False

    def _handle_death(self):
        """处理死亡：所有号复活"""
        logger.info("=== 检测到死亡，处理复活 ===")

        for i in range(len(self.wg.windows)):
            if self.screen.find_template("death_dialog", i):
                gw, gh = self.wg.windows[i].width, self.wg.windows[i].height
                # 点击复活按钮（对话框下方中央）
                self.screen.wg.switch_to(i)
                self.input.click(gw // 2, int(gh * 0.85), i)
                time.sleep(1)

        time.sleep(COMBAT.get("return_city_delay", 3000) / 1000.0)
        logger.info("所有号已复活")
        self._record_activity()

    # ─── 模式循环 ────────────────────────────

    def _loop_quest(self):
        """师门/日常任务循环"""
        leader = self.wg.leader

        # 1. 队长检查并接任务
        if leader.has_quest:
            logger.info("[队长] 已有任务，导航完成")
            self.navigator.go_to_objective(leader.index)
            leader.has_quest = False
        else:
            self.navigator.go_to_next_quest(leader.index)

        # 2. 队员检查任务标记
        for i in range(1, len(self.wg.windows)):
            if not self.wg.windows[i].has_quest:
                all_markers = self.screen.wg.detect_quest_markers()
                # 筛选属于该窗口的标记
                my_markers = [(wi, x, y) for wi, x, y in all_markers if wi == i]
                if my_markers:
                    logger.info(f"[号{i+1}] 检测到任务标记")
                    self.wg.windows[i].has_quest = True

        # 3. 战斗处理
        if self.combat.in_combat():
            self.combat.fight(self.wg)

        self._record_activity()

    def _loop_ghost(self):
        """捉鬼任务循环"""
        leader = self.wg.leader

        # 队长检查是否有鬼役NPC
        if not self.screen.find_template("quest_npc_flag", 0):
            logger.info("[队长] 检测不到鬼役NPC，去接捉鬼任务")
            self.navigator.go_to_next_quest(0)
            time.sleep(2)
            return

        # 进入捉鬼战斗
        if self.combat.in_combat():
            self.combat.fight(self.wg)
        else:
            # 队长与鬼役对话进入
            npc_pos = self.screen.find_template("quest_npc_flag", 0)
            if npc_pos:
                self.input.click(npc_pos[0], npc_pos[1], 0)
                time.sleep(1)

                # 点击确认进入战斗
                btn = self.screen.find_template("dialog_confirm", 0)
                if btn:
                    self.input.click(btn[0], btn[1], 0)
                    time.sleep(2)

        self._record_activity()

    def _loop_escort(self):
        """押镖循环"""
        if self.combat.in_combat():
            self.combat.fight(self.wg)
        else:
            logger.info("[押镖] 导航到镖师")
            self.navigator.go_to_next_quest(0)

        self._record_activity()

    def _loop_dungeon(self):
        """副本循环"""
        if self.combat.in_combat():
            self.combat.fight(self.wg)
        else:
            logger.info("[副本] 导航到副本入口")
            self.navigator.go_to_next_quest(0)

        self._record_activity()

    def _loop_story(self):
        """主线任务循环"""
        if self.combat.in_combat():
            self.combat.fight(self.wg)
        else:
            markers = self.screen.wg.detect_quest_markers()
            if markers:
                wi, x, y = markers[0]
                gw = self.wg.windows[wi]
                local_x, local_y = gw.screen_to_local(x, y)
                logger.info(f"[主线] 任务标记 窗口{wi} @ ({x},{y}) → 局部({local_x},{local_y})")
                self.input.click(local_x, local_y, wi)
            else:
                self.navigator.go_to_next_quest(0)

        self._record_activity()

    def _loop_treasure_map(self):
        """藏宝图挖掘循环"""
        logger.info("[藏宝图] 启动挖掘...")
        self.treasure_map.run(max_maps=10)
        self._record_activity()


def main():
    """入口"""
    mode = "quest"
    enable_ui = "--ui" in sys.argv

    if len(sys.argv) > 1 and sys.argv[1] not in ("--ui",):
        mode = sys.argv[1]

    bot = AutoBot(enable_ui=enable_ui)
    bot.run(mode, enable_ui=enable_ui)


if __name__ == "__main__":
    main()
