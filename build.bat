@echo off
chcp 65001 >nul
echo ========================================
echo Fallout76 Mod 助手 - Nuitka 编译脚本
echo ========================================
echo.

REM 检查 Nuitka 是否安装
python -m nuitka --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Nuitka，请先安装：
    echo pip install nuitka
    pause
    exit /b 1
)

echo [信息] 开始编译...
echo.

REM 清理之前的编译文件
if exist main.build (
    echo [清理] 删除旧的编译文件...
    rmdir /s /q main.build
)
if exist main.dist (
    echo [清理] 删除旧的发布目录...
    rmdir /s /q main.dist
)

echo.
echo [编译] 使用 Nuitka 编译主程序...
echo.

REM 软件信息配置
set PRODUCT_NAME=Fallout76 Mod Helper
set PRODUCT_VERSION=1.0.0.0
set FILE_VERSION=1.0.0.0
set COMPANY_NAME=Fallout76 Mod Helper
set FILE_DESCRIPTION=Fallout 76 Mod Manager
set COPYRIGHT=Copyright (c) 2025. Licensed under MIT License.

REM Nuitka 编译命令
python -m nuitka ^
    --standalone ^
    --windows-console-mode=force ^
    --windows-icon-from-ico=icon.ico ^
    --windows-company-name="%COMPANY_NAME%" ^
    --windows-product-name="%PRODUCT_NAME%" ^
    --windows-file-version="%FILE_VERSION%" ^
    --windows-product-version="%PRODUCT_VERSION%" ^
    --windows-file-description="%FILE_DESCRIPTION%" ^
    --copyright="%COPYRIGHT%" ^
    --output-filename=Fallout76ModHelper.exe ^
    --include-data-files=UnRAR.exe=UnRAR.exe ^
    --include-data-files=README.md=README.md ^
    --show-progress ^
    --show-memory ^
    --assume-yes-for-downloads ^
    --output-dir=build ^
    main.py

if errorlevel 1 (
    echo.
    echo [错误] 编译失败！
    pause
    exit /b 1
)

echo.
echo ========================================
echo [成功] 编译完成！
echo ========================================
echo.
echo 输出目录: build\main.dist\
echo.
echo 包含的文件：
echo   - Fallout76ModHelper.exe (主程序)
echo   - UnRAR.exe (RAR解压工具)
echo   - README.md (说明文档)
echo   - configs\ (配置目录，首次运行会自动创建)
echo.
echo 提示：
echo   1. 首次运行会在程序目录创建 configs\ 文件夹
echo   2. 确保 UnRAR.exe 在程序目录中
echo   3. 可以将整个 main.dist 文件夹打包分发
echo.
pause