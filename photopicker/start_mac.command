#!/usr/bin/env bash
# 拣影 · Mac 启动器
#
# 双击运行：自动装 Python + 依赖 + 检查更新 + 启动应用
# 没装过 Python 也没关系，会用 uv 自动下载一个独立的 Python。
#
# 第一次提示「无法打开，因为它来自身份不明的开发者」时：
#   右键（或按住 control 点击）→ 打开 → 在弹窗里再点「打开」即可，
#   之后双击就能直接运行。

set -e
export LC_ALL="${LC_ALL:-en_US.UTF-8}"
export LANG="${LANG:-en_US.UTF-8}"

cd "$(dirname "$0")"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  拣影 · 启动器"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ---- 1. 找 / 装 uv（Python 工具链管理器） ----
find_uv() {
  if command -v uv &>/dev/null; then
    echo "uv"
    return
  fi
  for cand in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv"; do
    if [ -x "$cand" ]; then
      echo "$cand"
      return
    fi
  done
}

UV="$(find_uv || true)"
if [ -z "$UV" ]; then
  echo ""
  echo "[首次准备] 正在安装 uv（Python 工具链管理器）..."
  echo "  这一步只在第一次运行做，之后秒过。"
  
  # 优先用 pip 安装（测试镜像源速度后选择最快的）
  PYTHON_CMD=""
  if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
  elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
  fi
  
  if [ -n "$PYTHON_CMD" ]; then
    echo "  测试镜像源速度..."
    # 简单测试几个源的速度
    MIRRORS=("https://mirrors.aliyun.com/pypi/simple/" "https://pypi.tuna.tsinghua.edu.cn/simple/" "https://pypi.mirrors.ustc.edu.cn/simple/")
    MIRROR_NAMES=("阿里云" "清华" "中科大")
    BEST_MIRROR=""
    BEST_TIME=999
    
    for i in "${!MIRRORS[@]}"; do
      START=$(date +%s%N 2>/dev/null || python3 -c "import time; print(int(time.time()*1000))")
      curl -s -o /dev/null -w "%{time_total}" "${MIRRORS[$i]}" --connect-timeout 2 2>/dev/null
      END=$(date +%s%N 2>/dev/null || python3 -c "import time; print(int(time.time()*1000))")
      # 简化：直接用第一个成功的源
      if curl -s -o /dev/null "${MIRRORS[$i]}" --connect-timeout 2 2>/dev/null; then
        BEST_MIRROR="${MIRRORS[$i]}"
        echo "  使用镜像源: ${MIRROR_NAMES[$i]}"
        break
      fi
    done
    
    if [ -z "$BEST_MIRROR" ]; then
      BEST_MIRROR="https://mirrors.aliyun.com/pypi/simple/"
    fi
    
    $PYTHON_CMD -m pip install uv -i "$BEST_MIRROR" --trusted-host mirrors.aliyun.com --trusted-host pypi.tuna.tsinghua.edu.cn --trusted-host pypi.mirrors.ustc.edu.cn 2>/dev/null
    UV="$(find_uv || true)"
  fi
  
  # 如果 pip 安装失败，尝试 curl 下载
  if [ -z "$UV" ]; then
    if command -v curl &>/dev/null; then
      echo "  使用 curl 下载 uv..."
      curl -LSf https://astral.sh/uv/install.sh | sh
      export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
      UV="$(find_uv || true)"
    fi
  fi
  
  if [ -z "$UV" ]; then
    echo ""
    echo "❌ uv 安装失败。"
    echo "   请手动安装 uv："
    echo "   1. 打开终端执行：pip3 install uv"
    echo "   2. 或访问 https://docs.astral.sh/uv/getting-started/installation/"
    echo ""
    read -n 1 -s -r -p "按任意键退出..."
    exit 1
  fi
  echo "  ✓ uv 安装完成"
fi

# 把 uv 自带的 Python 加进 PATH，确保后续 launcher.py 能调到
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# ---- 2. 用 uv 跑 launcher.py（uv 自动管理 Python 版本） ----
# 不加 --quiet：让 uv 下载 Python 的进度直接给用户看
# --no-project 防止 uv 误把当前目录当 uv 项目去解析 pyproject.toml
echo ""
echo "正在准备 Python 环境并启动 launcher..."
exec "$UV" run --no-project --python ">=3.10" -- python scripts/launcher.py
