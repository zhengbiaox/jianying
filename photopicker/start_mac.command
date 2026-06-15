#!/bin/bash
# PhotoPicker macOS 一键启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  PhotoPicker - 本地智能选片工具"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置国内镜像源
PIP_MIRROR="https://mirrors.aliyun.com/pypi/simple/"
NPM_MIRROR="https://registry.npmmirror.com"
HF_MIRROR="https://hf-mirror.com"

# 检测Python
echo "[1/4] 检测Python环境..."
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}错误: 未找到Python，请先安装Python 3.10+${NC}"
    echo "下载地址: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "${GREEN}✓ 找到 $PYTHON_VERSION${NC}"

# 检测Node.js
echo "[2/4] 检测Node.js环境..."
NODE_CMD=""
if command -v node &> /dev/null; then
    NODE_CMD="node"
    NODE_VERSION=$(node --version 2>&1)
    echo -e "${GREEN}✓ 找到 Node.js $NODE_VERSION${NC}"
else
    echo -e "${YELLOW}警告: 未找到Node.js，前端可能需要手动构建${NC}"
fi

# 安装Python依赖（使用阿里云镜像）
echo "[3/4] 检测并安装Python依赖..."
if [ -f "requirements.txt" ]; then
    echo "使用国内镜像源安装依赖..."
    $PYTHON_CMD -m pip install -r requirements.txt -i $PIP_MIRROR --trusted-host mirrors.aliyun.com 2>/dev/null || {
        echo -e "${YELLOW}正在安装依赖（首次运行需要下载，请耐心等待）...${NC}"
        $PYTHON_CMD -m pip install -r requirements.txt -i $PIP_MIRROR --trusted-host mirrors.aliyun.com
    }
    echo -e "${GREEN}✓ Python依赖已就绪${NC}"
else
    echo -e "${RED}错误: 未找到requirements.txt${NC}"
    exit 1
fi

# 构建前端（使用淘宝镜像）
echo "[4/4] 检测前端构建..."
if [ -d "frontend/dist" ] && [ -f "frontend/dist/index.html" ]; then
    echo -e "${GREEN}✓ 前端已构建${NC}"
elif [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    if [ -n "$NODE_CMD" ]; then
        echo "正在构建前端（使用淘宝镜像）..."
        cd frontend
        npm config set registry $NPM_MIRROR 2>/dev/null
        npm install --silent 2>/dev/null
        npm run build 2>/dev/null
        cd ..
        echo -e "${GREEN}✓ 前端构建完成${NC}"
    else
        echo -e "${YELLOW}跳过前端构建（需要Node.js）${NC}"
    fi
fi

echo ""
echo "=========================================="
echo "  启动服务..."
echo "=========================================="
echo ""
echo "访问地址: http://localhost:8010"
echo "按 Ctrl+C 停止服务"
echo ""

# 设置环境变量（HuggingFace镜像）
export HF_ENDPOINT=$HF_MIRROR

# 启动服务
$PYTHON_CMD -m uvicorn photopicker.backend.app:app --host 127.0.0.1 --port 8010 --reload
