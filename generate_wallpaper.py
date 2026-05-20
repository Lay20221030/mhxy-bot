# -*- coding: utf-8 -*-
"""生成 3840×2160 游戏窗口对齐壁纸"""

from PIL import Image, ImageDraw, ImageFont
import os

# 壁纸尺寸
WALL_W = 3840
WALL_H = 2160

# 每个方框尺寸（游戏窗口大小）
BOX_W = 1282
BOX_H = 1000

# 布局计算：3列 × 2行 = 6个格子
COLS = 3
ROWS = 2

# 水平间距（3个格子总宽 = 3*1282 = 3846，刚好比3840多6像素，让它们紧贴即可）
h_gap = (WALL_W - COLS * BOX_W) // (COLS + 1)  # 负值就紧贴
actual_box_w = BOX_W
# 每个格子的起始x
col_starts = []
current_x = max(0, h_gap)
for c in range(COLS):
    col_starts.append(current_x)
    current_x += actual_box_w + max(0, h_gap)

# 垂直间距
v_gap = (WALL_H - ROWS * BOX_H) // (ROWS + 1)
row_starts = []
current_y = v_gap
for r in range(ROWS):
    row_starts.append(current_y)
    current_y += BOX_H + v_gap

print(f"水平间距: {h_gap}px, 垂直间距: {v_gap}px")
print(f"列起始位置: {col_starts}")
print(f"行起始位置: {row_starts}")

# ─── 创建壁纸 ───
img = Image.new('RGB', (WALL_W, WALL_H), (18, 22, 28))  # 深色背景
draw = ImageDraw.Draw(img)

# 画背景网格
grid_color = (30, 36, 44)
for x in range(0, WALL_W, 128):
    draw.line([(x, 0), (x, WALL_H)], fill=grid_color, width=1)
for y in range(0, WALL_H, 128):
    draw.line([(0, y), (WALL_W, y)], fill=grid_color, width=1)

# 窗口标签
labels = [
    "号1 · 队长",
    "号2",
    "号3",
    "号4",
    "号5",
    "",
]

# 方框样式
box_fill = (24, 30, 38)          # 格子填充色
box_border = (60, 120, 200)      # 边框色（蓝色）
box_border_dimmed = (40, 50, 60) # 未使用格子边框色（深灰）

# 画方框
for r in range(ROWS):
    for c in range(COLS):
        idx = r * COLS + c
        x1 = col_starts[c]
        y1 = row_starts[r]
        x2 = x1 + BOX_W
        y2 = y1 + BOX_H

        label = labels[idx] if idx < len(labels) else ""
        is_used = bool(label)

        # 填充
        draw.rectangle([x1, y1, x2, y2], fill=box_fill)

        # 边框（带发光效果）
        border_color = box_border if is_used else box_border_dimmed
        border_width = 3 if is_used else 1

        # 外边框
        for i in range(border_width):
            draw.rectangle(
                [x1 - i, y1 - i, x2 + i, y2 + i],
                outline=border_color if i == 0 else tuple(max(0, c - 40) for c in border_color),
                width=1
            )

        # 四角加强标记
        corner_len = 30
        corner_w = 3
        corners = [
            # 左上
            [(x1, y1 + corner_len), (x1, y1), (x1 + corner_len, y1)],
            # 右上
            [(x2 - corner_len, y1), (x2, y1), (x2, y1 + corner_len)],
            # 左下
            [(x1, y2 - corner_len), (x1, y2), (x1 + corner_len, y2)],
            # 右下
            [(x2 - corner_len, y2), (x2, y2), (x2, y2 - corner_len)],
        ]
        for corner in corners:
            draw.line(corner, fill=box_border if is_used else (60, 60, 60), width=corner_w)

        # 标签文字
        if is_used:
            # 加载字体
            font_size = 48
            try:
                font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", font_size)
            except:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                except:
                    font = ImageFont.load_default()
            try:
                font_small = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 24)
            except:
                font_small = ImageFont.load_default()

            # 标签居中
            bbox = draw.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tx = x1 + (BOX_W - tw) // 2
            ty = y1 + (BOX_H - th) // 2

            # 文字阴影
            draw.text((tx + 2, ty + 2), label, fill=(0, 0, 0), font=font)
            # 文字主体
            draw.text((tx, ty), label, fill=(200, 220, 255), font=font)

            # 分辨率标注
            res_text = f"{BOX_W} × {BOX_H}"
            bbox2 = draw.textbbox((0, 0), res_text, font=font_small)
            rtw = bbox2[2] - bbox2[0]
            rtx = x1 + (BOX_W - rtw) // 2
            rty = ty + th + 16
            draw.text((rtx, rty), res_text, fill=(100, 120, 150), font=font_small)

# ─── 底部信息 ───
info_y = WALL_H - 60
try:
    font_info = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 20)
except:
    font_info = ImageFont.load_default()

info_lines = [
    "梦幻西游 · 5开窗口对齐壁纸  |  请将游戏窗口拖入对应方框  |  桌面缩放建议 125%",
    f"分辨率: {WALL_W}×{WALL_H}  |  每个窗口: {BOX_W}×{BOX_H}  |  列间距: {h_gap}px  行间距: {v_gap}px",
]
for i, line in enumerate(info_lines):
    bbox = draw.textbbox((0, 0), line, font=font_info)
    tw = bbox[2] - bbox[0]
    draw.text(((WALL_W - tw) // 2, info_y + i * 28), line, fill=(80, 90, 100), font=font_info)

# ─── 保存 ───
output_path = "/Users/lay/Desktop/梦幻西游5开对齐壁纸_3840x2160.png"
img.save(output_path, "PNG")
print(f"壁纸已保存: {output_path}")
print(f"文件大小: {os.path.getsize(output_path) / 1024:.1f} KB")
