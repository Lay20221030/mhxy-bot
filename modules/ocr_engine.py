# -*- coding: utf-8 -*-
"""
PaddleOCR 文字识别模块 (来自课件中的 ch_ppocr ONNX 模型)

游戏文字识别场景:
1. 任务面板 - 读取任务目标名称和坐标
2. NPC 对话 - 识别对话选项（我要去/请送我一程）
3. 地图名 - 识别当前所在地图名
4. 怪物名字 - 识别可攻击目标的名字
5. 验证码 - 文字选择类验证码识别

用法:
    ocr = OCREngine()
    text = ocr.recognize(image_region)  # 识别图片中的文字
    boxes = ocr.detect_text(image)       # 检测文字位置
"""

import logging
from typing import Optional, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# PaddleOCR 可选依赖
try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    logger.info("PaddleOCR 未安装，使用简易OCR兜底 (pip install paddleocr)")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class OCREngine:
    """OCR 文字识别引擎"""

    def __init__(self, use_paddle: bool = True, lang: str = "ch"):
        """
        Args:
            use_paddle: True=PaddleOCR(更准), False=Tesseract(更轻量)
            lang: 语言代码 ch=中文
        """
        self.ocr = None
        self.use_paddle = use_paddle and PADDLE_AVAILABLE

        if self.use_paddle:
            try:
                self.ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=lang,
                    use_gpu=False,  # CPU 模式
                    show_log=False,
                )
                logger.info("PaddleOCR 初始化成功")
            except Exception as e:
                logger.warning(f"PaddleOCR 初始化失败: {e}，回退到 Tesseract")
                self.use_paddle = False

    def recognize(self, image: np.ndarray) -> str:
        """识别图片中的所有文字，返回拼接字符串"""
        if self.use_paddle and self.ocr:
            return self._recognize_paddle(image)
        elif TESSERACT_AVAILABLE:
            return self._recognize_tesseract(image)
        else:
            return self._recognize_fallback(image)

    def detect_text_boxes(self, image: np.ndarray) -> List[Tuple[int, int, int, int, str]]:
        """检测文字位置和内容

        返回: [(left, top, right, bottom, text), ...]
        """
        if self.use_paddle and self.ocr:
            result = self.ocr.ocr(image, cls=True)
            if not result or not result[0]:
                return []

            boxes = []
            for line in result[0]:
                box = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text = line[1][0]  # 文字内容
                # 转为 (left, top, right, bottom)
                left = int(min(p[0] for p in box))
                top = int(min(p[1] for p in box))
                right = int(max(p[0] for p in box))
                bottom = int(max(p[1] for p in box))
                boxes.append((left, top, right, bottom, text))

            return boxes

        return []

    def find_text(self, image: np.ndarray, target: str) -> Optional[Tuple[int, int]]:
        """查找指定文字并返回中心坐标

        Args:
            image: 待搜索的图像
            target: 要查找的文字

        Returns:
            文字中心坐标 (x, y) 或 None
        """
        boxes = self.detect_text_boxes(image)
        for left, top, right, bottom, text in boxes:
            if target in text:
                cx = (left + right) // 2
                cy = (top + bottom) // 2
                return (cx, cy)
        return None

    # ─── PaddleOCR 实现 ────────────────────

    def _recognize_paddle(self, image: np.ndarray) -> str:
        result = self.ocr.ocr(image, cls=True)
        if not result or not result[0]:
            return ""

        texts = []
        for line in result[0]:
            text = line[1][0]
            confidence = line[1][1]
            if confidence > 0.5:  # 过滤低置信度
                texts.append(text)

        return " ".join(texts)

    # ─── Tesseract 实现 ────────────────────

    def _recognize_tesseract(self, image: np.ndarray) -> str:
        import cv2
        # 预处理：转灰度 + 二值化
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        text = pytesseract.image_to_string(binary, lang="chi_sim")
        return text.strip()

    # ─── 兜底实现 ──────────────────────────

    def _recognize_fallback(self, image: np.ndarray) -> str:
        """无 OCR 库时的兜底：按颜色检测文字区域数量"""
        import cv2

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # 检测亮色区域（白色/黄色文字）
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        text_regions = [c for c in contours if 30 < cv2.contourArea(c) < 5000]
        return f"[检测到 {len(text_regions)} 个文字区域]"

    # ─── 游戏特定识别 ──────────────────────

    def read_quest_panel(self, image: np.ndarray) -> dict:
        """从任务面板截图中提取任务信息

        返回: {"target_name": "xxx", "target_map": "xxx", "target_coords": (x, y)}
        """
        texts = self.recognize(image)
        result = {"target_name": "", "target_map": "", "target_coords": None}

        # 解析常见任务文本格式
        # 例如： "前往 大唐国境 寻找 强盗头目 (280, 40)"
        import re

        # 提取坐标
        coord_match = re.findall(r'[（(]\s*(\d+)\s*[,，]\s*(\d+)\s*[）)]', texts)
        if coord_match:
            result["target_coords"] = (int(coord_match[0][0]), int(coord_match[0][1]))

        # 提取地图名
        map_names = ["长安城", "建邺城", "傲来国", "长寿村", "大唐国境",
                      "大唐境外", "宝象国", "西梁女国", "东海湾", "江南野外"]
        for name in map_names:
            if name in texts:
                result["target_map"] = name
                break

        # 提取目标名（取地图名后面的文字）
        if result["target_map"]:
            parts = texts.split(result["target_map"])
            if len(parts) > 1:
                result["target_name"] = parts[1].strip()[:10]

        return result

    def read_dialog_option(self, image: np.ndarray) -> List[str]:
        """读取对话菜单选项"""
        boxes = self.detect_text_boxes(image)
        # 过滤出较长的文字（菜单选项通常 2-8 个字）
        options = []
        for _, _, _, _, text in boxes:
            if 2 <= len(text) <= 8:
                options.append(text)
        return options

    def read_current_map_name(self, image: np.ndarray) -> Optional[str]:
        """从截图中读取当前地图名（通常在小地图上方）"""
        texts = self.recognize(image)
        map_names = ["长安城", "建邺城", "傲来国", "长寿村", "大唐国境",
                      "大唐境外", "宝象国", "西梁女国", "东海湾", "江南野外"]
        for name in map_names:
            if name in texts:
                return name
        return None


# 全局实例
ocr_engine = None
