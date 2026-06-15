@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================
echo   PhotoPicker - 本地智能选片工具
echo ==========================================
echo.

cd /d "%~dp0"

REM 配置国内镜像源
set PIP_MIRROR=https://mirrors.aliyun.com/pypi/simple/
set NPM_MIRROR=https://registry.npmmirror.com
set HF_MIRROR=https://hf-mirror.com

REM 检测Python
echo [1/4] 检测Python环境...
set PYTHON_CMD=
where python >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=python
    goto :found_python
)
where python3 >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=python3
    goto :found_python
)
echo 错误: 未找到Python，请先安装Python 3.10+
echo 下载地址: https://www.python.org/downloads/
pause
exit /b 1

:found_python
for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✓ 找到 %PYTHON_VERSION%

REM 检测Node.js
echo [2/4] 检测Node.js环境...
set NODE_AVAILABLE=0
where node >nul 2>&1
if %errorlevel%==0 (
    set NODE_AVAILABLE=1
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
    echo ✓ 找到 Node.js !NODE_VERSION!
) else (
    echo 警告: 未找到Node.js，前端可能需要手动构建
)

REM 安装Python依赖（使用阿里云镜像）
echo [3/4] 检测并安装Python依赖...
if exist "requirements.txt" (
    echo 使用国内镜像源安装依赖...
    %PYTHON_CMD% -m pip install -r requirements.txt -i %PIP_MIRROR% --trusted-host mirrors.aliyun.com 2>nul
    if %errorlevel% neq 0 (
        echo 正在安装依赖（首次运行需要下载，请耐心等待）...
        %PYTHON_CMD% -m pip install -r requirements.txt -i %PIP_MIRROR% --trusted-host mirrors.aliyun.com
    )
    echo ✓ Python依赖已就绪
) else (
    echo 错误: 未找到requirements.txt
    pause
    exit /b 1
)

REM 构建前端（使用淘宝镜像）
echo [4/4] 检测前端构建...
if exist "frontend\dist\index.html" (
    echo ✓ 前端已构建
) else if exist "frontend\package.json" (
    if %NODE_AVAILABLE%==1 (
        echo 正在构建前端（使用淘宝镜像）...
        cd frontend
        call npm config set registry %NPM_MIRROR% 2>nul
        call npm install --silent 2>nul
        call npm run build 2>nul
        cd ..
        echo ✓ 前端构建完成
    ) else (
        echo 跳过前端构建（需要Node.js）
    )
)

echo.
echo ==========================================
echo   启动服务...
echo ==========================================
echo.
echo 访问地址: http://localhost:8010
echo 按 Ctrl+C 停止服务
echo.

REM 设置环境变量（HuggingFace镜像）
set HF_ENDPOINT=%HF_MIRROR%

REM 启动服务
%PYTHON_CMD% -m uvicorn photopicker.backend.app:app --host 127.0.0.1 --port 8010 --reload

pause
