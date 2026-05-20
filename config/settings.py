# -*- coding: utf-8 -*-
"""
梦幻西游自动脚本配置 - 多账号支持

窗口布局：5个游戏窗口并排排列
每个窗口有独立的 (x, y, width, height) 定义
"""

import os

# ════════════════════════════════════════
# 多账号窗口定义
# ════════════════════════════════════════

# 每个游戏窗口的屏幕坐标和尺寸
# 格式: (x, y, width, height) - 相对于屏幕左上角
# 根据实际窗口位置调整这些值

ACCOUNT_WINDOWS = [
    # 号1 (队长) - 窗口位置请根据实际调整
    {"name": "号1(队长)", "x": 0,     "y": 0,     "width": 1024, "height": 768},
    # 号2
    {"name": "号2",     "x": 1024,  "y": 0,     "width": 1024, "height": 768},
    # 号3
    {"name": "号3",     "x": 2048,  "y": 0,     "width": 1024, "height": 768},
    # 号4
    {"name": "号4",     "x": 3072,  "y": 0,     "width": 1024, "height": 768},
    # 号5
    {"name": "号5",     "x": 4096,  "y": 0,     "width": 1024, "height": 768},
]

# 屏幕总分辨率 (需要覆盖所有窗口)
SCREEN_RESOLUTION = (5120, 768)

# ════════════════════════════════════════
# 截图与识别设置
# ════════════════════════════════════════

MATCH_THRESHOLD = 0.85
RETRY_COUNT = 2
RECOGNIZE_INTERVAL = 0.2
AVG_SAMPLES = 2
SCREEN_SCALE = 0.5

TEMPLATES = {
    "quest_npc_flag":     "templates/quest_npc_flag.png",
    "quest_accept_btn":   "templates/quest_accept_btn.png",
    "quest_submit_btn":   "templates/quest_submit_btn.png",
    "dialog_continue":    "templates/dialog_continue.png",
    "dialog_confirm":     "templates/dialog_confirm.png",
    "dialog_close":       "templates/dialog_close.png",
    "combat_enemy_area":  "templates/combat_enemy_area.png",
    "combat_end_dialog":  "templates/combat_end_dialog.png",
    "death_dialog":       "templates/death_dialog.png",
    "captcha_dialog":     "templates/captcha_dialog.png",
    "treasure_map_icon":  "templates/treasure_map_icon.png",
}

# ════════════════════════════════════════
# 按键映射 (每个号独立)
# ════════════════════════════════════════

KEYS = {
    "map_key": "m",
    "quest_key": "j",
    "interact": "space",
    "confirm": "return",
    "cancel": "escape",
    "auto_combat": "f9",

    # 技能键 (所有号共用)
    "skill_1": "f1", "skill_2": "f2", "skill_3": "f3",
    "skill_4": "f4", "skill_5": "f5", "skill_6": "f6",
    "skill_7": "f7", "skill_8": "f8",

    # 药品
    "hp_potion": "f6",
    "mp_potion": "f7",

    # 切换目标
    "switch_target": "tab",
}

# ════════════════════════════════════════
# 通用设置
# ════════════════════════════════════════

COMMON = {
    "click_delay": 200,
    "key_delay": 150,
    "action_delay": 500,
    "post_action_wait": 800,

    # 随机延迟 (防检测，毫秒)
    "random_delay_min": 100,
    "random_delay_max": 400,

    "esc_count": 2,
}

# ════════════════════════════════════════
# 导航设置
# ════════════════════════════════════════

NAV = {
    "open_map_delay": 800,
    "auto_path_wait": 5000,
    "path_check_interval": 1000,
    "interact_delay": 600,
    "approach_wait": 2000,
    "dialog_wait": 400,
    "max_dialog_steps": 15,
}

# ════════════════════════════════════════
# 战斗设置 (多账号)
# ════════════════════════════════════════

COMBAT = {
    "combat_start_wait": 1500,
    "skill_interval": 300,        # 每个号技能间隔 (ms)
    "switch_account_delay": 200,  # 切换账号等待 (ms)

    # 技能循环
    "skill_rotation": [
        {"slot": 1, "type": "physical"},
        {"slot": 2, "type": "magic"},
        {"slot": 3, "type": "assist"},
    ],

    # 目标选择
    "target_mode": "lowest_hp",

    # 药品
    "hp_potion_threshold": 60,
    "mp_potion_threshold": 40,
    "potion_cooldown": 800,

    # 战斗结束
    "combat_end_wait": 2000,
    "combat_timeout": 120,

    # 死亡处理
    "death_auto_respawn": True,
    "return_city_delay": 3000,
}

# ════════════════════════════════════════
# 主循环设置
# ════════════════════════════════════════

LOOP = {
    "interval": 1.0,
    "mode": "all",

    "max_hours": 0,
    "auto_exit": True,

    "logging": True,
    "log_file": "logs/mhxy_bot.log",

    "hotkey_exit": "f11",
    "hotkey_pause": "f12",

    "stuck_detection": True,
    "stuck_timeout": 60,

    "after_daily": "wait",
    "wait_time": 60,
}

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")
