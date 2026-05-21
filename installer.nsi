; ─── 梦幻西游自动脚本 - NSIS 安装器脚本 ───
; 使用方法:
;   1. 安装 NSIS: https://nsis.sourceforge.io/Download
;   2. 先运行 build_exe.bat 生成 dist 目录
;   3. 打开 NSIS → 编译此脚本 → 生成 Setup.exe

!define PRODUCT_NAME "梦幻西游自动脚本"
!define PRODUCT_VERSION "2.0"
!define PRODUCT_PUBLISHER "MHXY Bot"
!define PRODUCT_URL "https://github.com/Lay20221030/mhxy-bot"

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "梦幻西游自动脚本_Setup.exe"
InstallDir "$PROGRAMFILES64\MHXY_Bot"
RequestExecutionLevel admin

SetCompressor /SOLID lzma

; ─── 界面设置 ───
!include "MUI2.nsh"
!define MUI_ABORTWARNING
!define MUI_ICON "install_icon.ico"

; 欢迎页
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; 语言
!insertmacro MUI_LANGUAGE "SimpChinese"

; ─── 安装段 ───
Section "Install"
    SetOutPath "$INSTDIR"

    ; 主程序
    File /r "dist\*.*"

    ; 创建开始菜单快捷方式
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\梦幻西游自动脚本.lnk" "$INSTDIR\梦幻西游自动脚本.exe"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\卸载.lnk" "$INSTDIR\uninstall.exe"

    ; 创建桌面快捷方式
    CreateShortCut "$DESKTOP\梦幻西游自动脚本.lnk" "$INSTDIR\梦幻西游自动脚本.exe"

    ; 写入注册表（用于卸载）
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "URLInfoAbout" "${PRODUCT_URL}"

    ; 创建卸载程序
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; ─── 卸载段 ───
Section "Uninstall"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\${PRODUCT_NAME}\*.*"
    RMDir "$SMPROGRAMS\${PRODUCT_NAME}"
    Delete "$DESKTOP\梦幻西游自动脚本.lnk"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
SectionEnd
