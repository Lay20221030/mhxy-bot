# -*- coding: utf-8 -*-
"""
一键打包脚本 - 生成可分发的安装包

用法:
    python build_package.py          # 打包当前平台的可执行文件
    python build_package.py --all    # 打包 + 生成 ZIP 安装包
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DIST_DIR = PROJECT_DIR / "dist"
BUILD_DIR = PROJECT_DIR / "build"
PACKAGE_NAME = "梦幻西游自动脚本_v2.0"


def clean():
    """清理旧构建"""
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            shutil.rmtree(d)
    for f in PROJECT_DIR.glob("*.spec"):
        f.unlink()
    print("[OK] 清理完成")


def install_pyinstaller():
    """安装 PyInstaller"""
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "--quiet"],
                   check=True)
    print("[OK] PyInstaller 已安装")


def build_exe():
    """构建可执行文件"""
    print("\n[构建] 正在打包...")
    print("  这可能需要 3-5 分钟，请耐心等待...\n")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # 单文件输出
        "--windowed",                   # 无控制台窗口
        f"--name={PACKAGE_NAME}",
        "--add-data", f"config{os.pathsep}config",
        "--add-data", f"core{os.pathsep}core",
        "--add-data", f"modules{os.pathsep}modules",
        "--add-data", f"templates{os.pathsep}templates",
        "--hidden-import", "cv2",
        "--hidden-import", "numpy",
        "--hidden-import", "mss",
        "--hidden-import", "pyautogui",
        "--hidden-import", "PIL",
        "--hidden-import", "keyboard",
        "--hidden-import", "PyQt5",
        "--hidden-import", "config.settings",
        "--hidden-import", "core.window_group",
        "--hidden-import", "core.screen",
        "--hidden-import", "core.input_sim",
        "--hidden-import", "core.captcha",
        "--hidden-import", "core.flow_control",
        "--hidden-import", "core.session_manager",
        "--hidden-import", "modules.combat",
        "--hidden-import", "modules.navigation",
        "--hidden-import", "modules.teleport",
        "--hidden-import", "modules.station_coach",
        "--hidden-import", "modules.task_reader",
        "--hidden-import", "modules.bandit_hunt",
        "--hidden-import", "modules.escort_landmark",
        "--hidden-import", "modules.warehouse",
        "--hidden-import", "modules.ocr_engine",
        "--hidden-import", "modules.tasks.sect_quest",
        "--hidden-import", "modules.tasks.ghost_hunt",
        "--hidden-import", "modules.tasks.treasure_map",
        str(PROJECT_DIR / "launcher.py"),
    ]

    result = subprocess.run(cmd, cwd=str(PROJECT_DIR))
    if result.returncode != 0:
        print("\n[错误] 打包失败！")
        return None

    # PyInstaller 输出在 dist/ 下
    exe_name = f"{PACKAGE_NAME}.exe" if sys.platform == "win32" else PACKAGE_NAME
    exe_path = DIST_DIR / exe_name

    if not exe_path.exists():
        # 可能在子目录里
        candidates = list(DIST_DIR.glob("**/*.exe"))
        if candidates:
            exe_path = candidates[0]

    print(f"\n[OK] 打包完成: {exe_path}")
    print(f"  文件大小: {exe_path.stat().st_size / (1024*1024):.1f} MB")
    return exe_path


def create_release_dir(exe_path):
    """创建发布目录结构"""
    release_dir = PROJECT_DIR / "release" / PACKAGE_NAME
    release_dir.mkdir(parents=True, exist_ok=True)

    # 复制可执行文件
    shutil.copy(exe_path, release_dir)

    # 创建必要目录
    for subdir in ["logs", "templates", "config"]:
        (release_dir / subdir).mkdir(exist_ok=True)

    # 创建使用说明
    readme = release_dir / "使用说明.txt"
    readme.write_text("""梦幻西游自动脚本 v2.0 - 使用说明
=====================================

【首次使用】
1. 双击运行 "梦幻西游自动脚本_v2.0.exe"
2. 在界面中配置 5 个游戏窗口的坐标
3. 在 templates/ 目录下放入模板截图（详见下方说明）
4. 选择任务模式 → 点击启动

【快捷键】
  F12 = 暂停 / 恢复
  F11 = 退出脚本

【模板截图】
  至少需要以下 6 个模板（放入 templates/ 目录）：
  - dialog_confirm.png    (对话框确认按钮)
  - combat_enemy_area.png  (敌人区域)
  - combat_end_dialog.png  (战斗结束弹窗)
  - quest_npc_flag.png    (NPC 任务标记)
  - death_dialog.png      (死亡对话框)
  - captcha_dialog.png    (验证码对话框)

  截图方法：QQ 截图 (Ctrl+Alt+A) → 框选元素 → 保存为 PNG

【配置文件】
  窗口坐标和所有设置都在 config/settings.py 中。
  启动器界面修改的配置会自动覆盖。

【技术支持】
  GitHub: https://github.com/Lay20221030/mhxy-bot

【注意】
  仅供个人学习使用，禁止用于商业用途。
""", encoding="utf-8")

    print(f"\n[OK] 发布目录: {release_dir}")
    return release_dir


def create_zip(release_dir):
    """创建 ZIP 压缩包"""
    import zipfile

    zip_path = PROJECT_DIR / f"{PACKAGE_NAME}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(release_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(release_dir.parent)
                zf.write(file_path, arcname)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"[OK] ZIP 包: {zip_path}  ({size_mb:.1f} MB)")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="梦幻西游自动脚本 打包工具")
    parser.add_argument("--all", action="store_true", help="生成 ZIP 安装包")
    parser.add_argument("--clean", action="store_true", help="只清理构建")
    args = parser.parse_args()

    if args.clean:
        clean()
        return

    print("=" * 50)
    print("  梦幻西游自动脚本 - 一键打包")
    print("=" * 50)

    clean()
    install_pyinstaller()
    exe_path = build_exe()

    if exe_path and args.all:
        release_dir = create_release_dir(exe_path)
        create_zip(release_dir)
        print(f"\n{'=' * 50}")
        print(f"  全部完成！")
        print(f"  可执行文件: {exe_path}")
        print(f"  ZIP 安装包: {PROJECT_DIR}/{PACKAGE_NAME}.zip")
        print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
