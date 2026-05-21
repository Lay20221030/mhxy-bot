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
    # 号1 (队长) - 左上  |  对齐壁纸第一行第一列
    {"name": "号1(队长)", "x": 0,     "y": 53,    "width": 1282, "height": 1000},
    # 号2 - 中上  |  对齐壁纸第一行第二列
    {"name": "号2",     "x": 1282,  "y": 53,    "width": 1282, "height": 1000},
    # 号3 - 右上  |  对齐壁纸第一行第三列
    {"name": "号3",     "x": 2564,  "y": 53,    "width": 1282, "height": 1000},
    # 号4 - 左下  |  对齐壁纸第二行第一列
    {"name": "号4",     "x": 0,     "y": 1106,  "width": 1282, "height": 1000},
    # 号5 - 中下  |  对齐壁纸第二行第二列
    {"name": "号5",     "x": 1282,  "y": 1106,  "width": 1282, "height": 1000},
]

# 屏幕总分辨率 (4K 显示器，桌面缩放 125%)
SCREEN_RESOLUTION = (3840, 2160)

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
    "fly_flag_icon":      "templates/fly_flag_icon.png",
    "fly_scroll_icon":    "templates/fly_scroll_icon.png",
    "backpack_open":      "templates/backpack_open.png",
    "warehouse_npc":      "templates/warehouse_npc.png",
    "friend_icon":        "templates/friend_icon.png",
    "login_button":       "templates/login_button.png",
    "login_screen":       "templates/login_screen.png",
    "disconnect_dialog":  "templates/disconnect_dialog.png",
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

    # ─── 地图坐标映射 (教程第11课) ───
    # 游戏地图像素宽高 (截取的地图区域)
    "map_width": 545,
    "map_height": 276,
    # 地图最大 XY 坐标
    "max_map_x": 548,
    "max_map_y": 547,

    # ─── 坐标点击偏移 (教程第14课) ───
    # 基准偏移量 (窗口左上角到地图区域的偏移)
    "base_click_x": 400,
    "base_click_y": 300,
    "scale_factor": 1.0,

    # ─── 遮挡处理 (教程第15课) ───
    "unblock_max_retries": 3,
    "unblock_ctrl_trigger": True,
    "unblock_wait_moving": 3.0,

    # ─── 新区/老区差异化 (教程第28课) ───
    # 新区人多卡顿，需要更长延时和更多重试
    "new_district_mode": False,      # 是否新区模式
    "new_district_delay_mult": 1.5,  # 新区延时倍率
    "new_district_retry_mult": 2,    # 新区重试倍率

    # ─── 飞行旗目的地映射 ───
    "fly_destinations": {
        "长安城":  {"x": 100, "y": 200},
        "建邺城":  {"x": 200, "y": 100},
        "傲来国":  {"x": 300, "y": 150},
        "长寿村":  {"x": 150, "y": 300},
        "大唐国境": {"x": 280, "y": 40},
        "大唐境外": {"x": 100, "y": 50},
        "西梁女国": {"x": 400, "y": 100},
        "宝象国":  {"x": 350, "y": 200},
    },
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
