# -*- coding: utf-8 -*-
"""
梦幻西游自动脚本 - 图形化启动器

双击运行，无需命令行。支持：
- 下拉选择模式
- 窗口数量/坐标配置
- 一键启动/暂停/退出
- 实时状态显示
"""

import sys
import time
import threading
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QGroupBox, QGridLayout,
    QTextEdit, QSpinBox, QCheckBox, QMessageBox, QFrame, QSplitter,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon


class ModeConfig:
    """模式配置"""
    MODES = {
        "quest": "师门任务",
        "ghost": "捉鬼任务",
        "treasure_map": "藏宝图挖掘",
        "escort": "押镖",
        "dungeon": "副本",
        "story": "主线任务",
    }


class LauncherWindow(QMainWindow):
    """主启动器窗口"""

    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str, str)  # (label, text)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("梦幻西游自动脚本 v2.0")
        self.setMinimumSize(800, 600)

        # 脚本实例
        self.bot = None
        self.bot_thread = None

        # 日志缓冲
        self.log_lines = []
        self.log_signal.connect(self._append_log)
        self.status_signal.connect(self._update_status)

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # ─── 顶部：标题 ───
        title = QLabel("梦幻西游 · 全自动多账号脚本")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1a56db; padding: 10px;")
        main_layout.addWidget(title)

        # ─── 模式选择区 ───
        mode_group = QGroupBox("任务模式")
        mode_layout = QHBoxLayout(mode_group)

        mode_layout.addWidget(QLabel("选择模式："))
        self.mode_combo = QComboBox()
        for key, name in ModeConfig.MODES.items():
            self.mode_combo.addItem(name, key)
        self.mode_combo.setMinimumWidth(150)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()

        self.ui_check = QCheckBox("显示控制面板")
        self.ui_check.setChecked(True)
        mode_layout.addWidget(self.ui_check)

        main_layout.addWidget(mode_group)

        # ─── 窗口配置区 ───
        win_group = QGroupBox("窗口配置")
        win_layout = QGridLayout(win_group)

        self.win_spinboxes = []
        headers = ["窗口", "X坐标", "Y坐标", "宽度", "高度"]
        for col, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
            win_layout.addWidget(lbl, 0, col)

        for i in range(5):
            is_leader = i == 0
            name = f"号{i+1}{'(队长)' if is_leader else ''}"
            win_layout.addWidget(QLabel(name), i + 1, 0)

            spinners = []
            default_vals = [
                [0, 1282, 2564, 0, 1282],      # x
                [53, 53, 53, 1106, 1106],       # y
                [1282] * 5,                       # w
                [1000] * 5,                       # h
            ]
            for col in range(4):
                spin = QSpinBox()
                spin.setRange(0, 9999)
                spin.setValue(default_vals[col][i])
                spin.setMaximumWidth(80)
                spinners.append(spin)
                win_layout.addWidget(spin, i + 1, col + 1)

            self.win_spinboxes.append(spinners)

        main_layout.addWidget(win_group)

        # ─── 控制按钮区 ───
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("▶  启动脚本")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a56db; color: white; font-size: 14px;
                font-weight: bold; border-radius: 5px; padding: 8px 20px;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled { background-color: #6b7280; }
        """)
        self.start_btn.clicked.connect(self._start_bot)
        btn_layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("⏸  暂停")
        self.pause_btn.setMinimumHeight(40)
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._toggle_pause)
        btn_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("⏹  停止")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_bot)
        btn_layout.addWidget(self.stop_btn)

        main_layout.addLayout(btn_layout)

        # ─── 状态栏 ───
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel)
        status_layout = QHBoxLayout(status_frame)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("font-weight: bold; color: #10b981;")
        status_layout.addWidget(QLabel("状态："))
        status_layout.addWidget(self.status_label)

        self.mode_status = QLabel("模式：未启动")
        status_layout.addWidget(self.mode_status)
        status_layout.addStretch()

        self.time_label = QLabel("运行时间：--")
        status_layout.addWidget(self.time_label)

        main_layout.addWidget(status_frame)

        # ─── 日志区 ───
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)

        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(lambda: self.log_text.clear())
        log_layout.addWidget(clear_btn)

        main_layout.addWidget(log_group)

    # ─── 脚本控制 ───

    def _start_bot(self):
        """启动脚本"""
        mode = self.mode_combo.currentData()

        # 读取窗口配置
        windows = []
        for i, spins in enumerate(self.win_spinboxes):
            windows.append({
                "name": f"号{i+1}{'(队长)' if i == 0 else ''}",
                "x": spins[0].value(),
                "y": spins[1].value(),
                "width": spins[2].value(),
                "height": spins[3].value(),
            })

        # 计算屏幕分辨率
        max_x = max(w["x"] + w["width"] for w in windows)
        max_y = max(w["y"] + w["height"] for w in windows)

        self._log(f"启动模式: {ModeConfig.MODES.get(mode, mode)}")
        self._log(f"窗口数: {len(windows)} 个, 屏幕: {max_x}×{max_y}")

        # 在后台线程中运行
        def run_bot():
            try:
                from config.settings import ACCOUNT_WINDOWS, SCREEN_RESOLUTION
                # 临时覆盖配置
                import config.settings as settings
                settings.ACCOUNT_WINDOWS = windows
                settings.SCREEN_RESOLUTION = (max_x, max_y)

                from main import AutoBot
                self.bot = AutoBot(enable_ui=self.ui_check.isChecked())
                self.bot_thread = threading.current_thread()

                # 重定向日志到 UI
                import logging
                ui_handler = UILogHandler(self.log_signal)
                ui_handler.setFormatter(
                    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
                logging.getLogger().addHandler(ui_handler)

                self.status_signal.emit("status", "运行中")
                self.status_signal.emit("mode", f"模式：{ModeConfig.MODES.get(mode, mode)}")

                self.bot.run(mode)
            except Exception as e:
                self.log_signal.emit(f"错误: {e}")
            finally:
                self.status_signal.emit("status", "已停止")

        thread = threading.Thread(target=run_bot, daemon=True)
        thread.start()

        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.mode_combo.setEnabled(False)

        # 计时器
        self._start_time = time.time()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_runtime)
        self._timer.start(1000)

    def _toggle_pause(self):
        if self.bot:
            self.bot.paused = not self.bot.paused
            state = "已暂停" if self.bot.paused else "运行中"
            self.pause_btn.setText("▶  恢复" if self.bot.paused else "⏸  暂停")
            self._log(f"脚本 {state}")
            self.status_signal.emit("status", state)

    def _stop_bot(self):
        if self.bot:
            self.bot.running = False
        self._log("正在停止脚本...")
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.mode_combo.setEnabled(True)
        if hasattr(self, '_timer'):
            self._timer.stop()
        self.status_signal.emit("status", "已停止")

    def _update_runtime(self):
        if hasattr(self, '_start_time'):
            elapsed = int(time.time() - self._start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            self.time_label.setText(f"运行时间：{h:02d}:{m:02d}:{s:02d}")

    # ─── 日志和状态更新（线程安全） ───

    def _log(self, msg):
        self.log_signal.emit(msg)

    def _append_log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{ts}] {msg}")

    def _update_status(self, label, text):
        if label == "status":
            color = {"运行中": "#10b981", "已暂停": "#f59e0b", "已停止": "#ef4444"}.get(text, "#6b7280")
            self.status_label.setText(text)
            self.status_label.setStyleSheet(f"font-weight: bold; color: {color};")
        elif label == "mode":
            self.mode_status.setText(text)

    def closeEvent(self, event):
        if self.bot and self.bot.running:
            reply = QMessageBox.question(
                self, '确认退出', '脚本正在运行中，确定要退出吗？',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.bot.running = False
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


class UILogHandler(logging.Handler):
    """将日志发送到 UI"""

    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def emit(self, record):
        msg = self.format(record)
        self.signal.emit(msg)


def main():
    import logging
    app = QApplication(sys.argv)

    # 暗色主题
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(30, 30, 40))
    palette.setColor(QPalette.WindowText, QColor(220, 220, 230))
    palette.setColor(QPalette.Base, QColor(25, 25, 35))
    palette.setColor(QPalette.Text, QColor(220, 220, 230))
    palette.setColor(QPalette.Button, QColor(45, 45, 55))
    palette.setColor(QPalette.ButtonText, QColor(220, 220, 230))
    app.setPalette(palette)

    window = LauncherWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    import logging
    main()
