# -*- coding: utf-8 -*-
"""
可视化 UI 面板

基于 PyQt5，提供：
1. 实时状态显示（各窗口状态、战斗状态、任务标记）
2. 模式切换（师门/捉鬼/押镖/副本/主线）
3. 暂停/恢复/退出控制
4. 日志实时查看
"""

import sys
import time
import logging
from typing import Optional
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QTextEdit, QGroupBox, QGridLayout, QProgressBar,
    QComboBox, QFrame,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont

logger = logging.getLogger(__name__)


class LogHandler(logging.Handler):
    """将日志输出到 UI 面板"""

    def __init__(self, text_edit: QTextEdit):
        super().__init__()
        self.text_edit = text_edit

    def emit(self, record):
        msg = self.format(record)
        # 在主线程中更新 UI
        QTimer.singleShot(0, lambda: self._append(msg))

    def _append(self, msg):
        self.text_edit.append(msg)
        # 自动滚动到底部
        scrollbar = self.text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class StatusCard(QGroupBox):
    """单个窗口状态卡片"""

    def __init__(self, name: str, parent=None):
        super().__init__(name, parent)

        layout = QGridLayout(self)

        self.combat_label = QLabel("不在战斗")
        self.quest_label = QLabel("无任务")
        self.hp_label = QLabel("HP: --%")
        self.mp_label = QLabel("MP: --%")

        layout.addWidget(QLabel("战斗:"), 0, 0)
        layout.addWidget(self.combat_label, 0, 1)
        layout.addWidget(QLabel("任务:"), 1, 0)
        layout.addWidget(self.quest_label, 1, 1)
        layout.addWidget(QLabel("HP:"), 2, 0)
        layout.addWidget(self.hp_label, 2, 1)
        layout.addWidget(QLabel("MP:"), 3, 0)
        layout.addWidget(self.mp_label, 3, 1)

    def update_status(self, in_combat: bool, has_quest: bool,
                      hp_percent: Optional[float] = None, mp_percent: Optional[float] = None):
        self.combat_label.setText("战斗中" if in_combat else "正常")
        self.combat_label.setStyleSheet(
            f"color: {'red' if in_combat else 'green'}; font-weight: bold")
        self.quest_label.setText("有任务" if has_quest else "无任务")
        if hp_percent is not None:
            self.hp_label.setText(f"HP: {hp_percent:.0f}%")
            color = "red" if hp_percent < 30 else ("orange" if hp_percent < 60 else "green")
            self.hp_label.setStyleSheet(f"color: {color}")
        if mp_percent is not None:
            self.mp_label.setText(f"MP: {mp_percent:.0f}%")
            color = "blue" if mp_percent < 30 else ("cyan" if mp_percent < 60 else "green")
            self.mp_label.setStyleSheet(f"color: {color}")


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self, bot=None):
        super().__init__()
        self.bot = bot
        self.setWindowTitle("梦幻西游自动脚本 - 控制面板")
        self.setMinimumSize(900, 650)

        # 状态轮询定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_status)
        self.timer.start(1000)  # 每秒更新

        self._build_ui()

    def _build_ui(self):
        """构建 UI"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # 左侧：状态面板
        left_panel = self._build_left_panel()
        main_layout.addWidget(left_panel, 2)

        # 右侧：日志面板
        right_panel = self._build_right_panel()
        main_layout.addWidget(right_panel, 1)

    def _build_left_panel(self) -> QWidget:
        """构建左侧状态面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 标题
        title = QLabel("梦幻西游自动脚本")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 运行状态
        status_group = QGroupBox("运行状态")
        status_layout = QVBoxLayout(status_group)

        self.mode_label = QLabel("模式: 师门任务")
        self.status_label = QLabel("状态: 运行中")
        self.mode_label.setStyleSheet("font-size: 14px; font-weight: bold")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold")
        status_layout.addWidget(self.mode_label)
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_group)

        # 窗口状态卡片
        self.window_cards = []
        cards_group = QGroupBox("账号状态")
        cards_layout = QVBoxLayout(cards_group)

        for i in range(5):
            card = StatusCard(f"号{i+1}")
            self.window_cards.append(card)
            cards_layout.addWidget(card)

        layout.addWidget(cards_group)

        # 控制按钮
        btn_layout = QHBoxLayout()
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self._on_pause)
        btn_layout.addWidget(self.pause_btn)

        self.exit_btn = QPushButton("退出")
        self.exit_btn.clicked.connect(self._on_exit)
        btn_layout.addWidget(self.exit_btn)

        self.restart_btn = QPushButton("重启")
        self.restart_btn.clicked.connect(self._on_restart)
        btn_layout.addWidget(self.restart_btn)

        layout.addLayout(btn_layout)
        return panel

    def _build_right_panel(self) -> QWidget:
        """构建右侧日志面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        title = QLabel("运行日志")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        layout.addWidget(title)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))

        # 添加日志处理器
        handler = LogHandler(self.log_text)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logging.getLogger().addHandler(handler)

        layout.addWidget(self.log_text)

        # 清空按钮
        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(lambda: self.log_text.clear())
        layout.addWidget(clear_btn)

        return panel

    def _update_status(self):
        """更新状态显示"""
        if not self.bot:
            return

        # 更新模式标签
        mode_map = {
            "quest": "师门任务",
            "ghost": "捉鬼任务",
            "escort": "押镖",
            "dungeon": "副本",
            "story": "主线任务",
        }
        mode = mode_map.get(self.bot.current_mode, self.bot.current_mode)
        self.mode_label.setText(f"模式: {mode}")

        # 更新运行状态
        if self.bot.paused:
            self.status_label.setText("状态: 已暂停")
            self.status_label.setStyleSheet("color: orange; font-size: 14px; font-weight: bold")
            self.pause_btn.setText("恢复")
        else:
            self.status_label.setText("状态: 运行中")
            self.status_label.setStyleSheet("color: green; font-size: 14px; font-weight: bold")
            self.pause_btn.setText("暂停")

        # 更新窗口状态卡片
        for i, card in enumerate(self.window_cards):
            if i < len(self.bot.wg.windows):
                win = self.bot.wg.windows[i]
                card.update_status(
                    in_combat=win.in_combat,
                    has_quest=win.has_quest,
                )

    def _on_pause(self):
        if self.bot:
            self.bot.paused = not self.bot.paused

    def _on_exit(self):
        if self.bot:
            self.bot.running = False

    def _on_restart(self):
        if self.bot:
            self.bot.running = False
            # 触发重启（由外部处理）


def run_ui(bot=None):
    """启动 UI 面板"""
    app = QApplication(sys.argv)
    window = MainWindow(bot)
    window.show()
    sys.exit(app.exec_())
