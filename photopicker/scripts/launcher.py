"""拣影 · 启动器（Python 部分）

由 start_mac.command / start_windows.bat 调用。
本脚本只用标准库，可以在任何 Python 3.10+ 下运行。

职责：
1. 询问用户启用哪些模式（首次），按选择装依赖
2. 启动 app.py，等待退出

约定：
- 项目根目录 = 本脚本所在目录的父目录
- venv 位于项目根目录的 .venv/
- 依赖安装记录在 .photopicker_install.json
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT.parent  # /Users/zhengbiao/chat
VENV = ROOT / ".venv"
INSTALL_INFO = ROOT / ".photopicker_install.json"

IS_WIN = os.name == "nt"
PY_IN_VENV = VENV / ("Scripts" if IS_WIN else "bin") / ("python.exe" if IS_WIN else "python")

# 国内镜像源
PYPI_MIRRORS = [
    ("https://mirrors.aliyun.com/pypi/simple/", "mirrors.aliyun.com（阿里云）"),
    ("https://pypi.tuna.tsinghua.edu.cn/simple/", "pypi.tuna.tsinghua.edu.cn（清华大学）"),
    ("https://mirrors.cernet.edu.cn/pypi/web/simple", "mirrors.cernet.edu.cn（教育网）"),
    ("https://pypi.mirrors.ustc.edu.cn/simple/", "pypi.mirrors.ustc.edu.cn（中科大）"),
    ("https://mirrors.huaweicloud.com/pypi/simple/", "mirrors.huaweicloud.com（华为云）"),
]
HF_MIRROR = "https://hf-mirror.com"

# 模式配置
CORE_PACKAGES = [
    "fastapi",
    "uvicorn[standard]",
    "pydantic>=2.0",
    "opencv-python-headless",
    "Pillow>=10.0",
    "pillow-heif>=0.16",
    "numpy>=1.26",
    "imagehash>=4.3",
    "rawpy>=0.18",
    "mediapipe",
]

MODE_PACKAGES = {
    "basic": [],  # 基础模式，只用 CORE
    "full": [     # 完整模式，包含深度学习
        "torch>=2.2",
        "torchvision>=0.17",
        "open-clip-torch",
        "transformers>=4.40",
        "huggingface-hub",
        "safetensors",
        "scikit-learn",
    ],
    "ai": [       # AI 增强模式，包含人脸/美学检测
        "torch>=2.2",
        "torchvision>=0.17",
        "open-clip-torch",
        "transformers>=4.40",
        "huggingface-hub",
        "safetensors",
        "scikit-learn",
        "insightface>=0.7",
        "onnxruntime>=1.16",
    ],
}

MODE_LABELS = {
    "basic": "基础模式（轻量，约 200MB，下载 1-3 分钟）\n"
             "        • 自动识别模糊、过曝、闭眼等废片\n"
             "        • 按颜色、拍摄时间自动分组\n"
             "        • 适合日常随手拍的照片筛选",
    "full": "完整模式（推荐，约 1-2GB，下载 3-10 分钟）\n"
            "        • 基础模式全部功能\n"
            "        • AI 理解照片内容（风景/人像/美食等）\n"
            "        • 分组更精准，相似照片归类更合理",
    "ai": "AI 增强模式（最强，约 2-3GB，下载 5-15 分钟）\n"
          "        • 完整模式全部功能\n"
          "        • 自动识别照片中的人物并分组\n"
          "        • AI 给每张照片打颜值分\n"
          "        • 适合人像、婚礼、聚会照片",
}

# ---------- 输出 ----------

def banner(text: str) -> None:
    print()
    print("━" * 56)
    print(f"  {text}")
    print("━" * 56)


def step(idx: int, total: int, text: str) -> None:
    print(f"\n[{idx}/{total}] {text}")


def info(text: str) -> None:
    print(f"  • {text}")


def warn(text: str) -> None:
    print(f"  ⚠ {text}")


def die(text: str) -> None:
    print(f"\n❌ {text}", file=sys.stderr)
    print("\n按回车键退出...", file=sys.stderr)
    try:
        input()
    except EOFError:
        pass
    sys.exit(1)


# ---------- 安装信息持久化 ----------

def load_install() -> dict:
    if INSTALL_INFO.exists():
        try:
            return json.loads(INSTALL_INFO.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_install(data: dict) -> None:
    INSTALL_INFO.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------- 模式选择 ----------

def ask_modes(previous: list[str] | None) -> list[str]:
    if previous:
        info(f"使用上次配置的模式：{', '.join(previous)}")
        return previous

    # 非交互模式（如管道输入）：默认使用完整模式
    if not sys.stdin.isatty():
        info("非交互模式，使用默认：完整模式")
        return ["full"]

    print()
    print("第一次运行，请选择要启用的模式（可多选，逗号或空格分隔）：")

    print()
    keys = ["basic", "full", "ai"]
    for i, key in enumerate(keys, 1):
        print(f"  {i}) {MODE_LABELS[key]}")
        print()
    print(f"  4) 全部（AI 增强模式，推荐）")

    while True:
        try:
            raw = input("\n> ").strip()
        except EOFError:
            raw = ""

        if not raw:
            print("请至少选一个。")
            continue

        tokens = re.findall(r"[1-4]", raw)
        if not tokens:
            print("无法识别，请输入 1-4 的数字。")
            continue

        if "4" in tokens:
            return ["ai"]

        chosen = []
        for t in tokens:
            k = keys[int(t) - 1]
            if k not in chosen:
                chosen.append(k)
        if not chosen:
            print("请至少选一个。")
            continue
        return chosen


def ask_runtime(previous: str | None) -> str:
    if previous:
        info(f"使用上次配置的运行设备：{previous}")
        return previous

    # 非交互模式：默认自动检测
    if not sys.stdin.isatty():
        info("非交互模式，使用默认：自动检测")
        return "auto"

    print()
    print("请选择本地运行时设备偏好：")

    print()
    print("  1) auto  自动（检测到可用 GPU 就优先用）")
    print("  2) cpu   只用 CPU")
    print("  3) gpu   强制用 GPU（没有可用 GPU 就报错）")

    mapping = {"1": "auto", "2": "cpu", "3": "gpu"}
    while True:
        try:
            raw = input("\n> ").strip().lower()
        except EOFError:
            raw = ""

        if raw in {"auto", "cpu", "gpu"}:
            return raw
        if raw in mapping:
            return mapping[raw]
        print("无法识别，请输入 1/2/3 或 auto/cpu/gpu。")


# ---------- uv 管理 ----------

def find_uv() -> str | None:
    if shutil.which("uv"):
        return "uv"
    for cand in [
        Path.home() / ".local" / "bin" / ("uv.exe" if IS_WIN else "uv"),
        Path.home() / ".cargo" / "bin" / ("uv.exe" if IS_WIN else "uv"),
    ]:
        if cand.exists():
            return str(cand)
    return None


def install_uv() -> str | None:
    info("正在下载 uv（Python 工具链，~30MB）...")
    info("这一步只在第一次运行做，之后秒过。")

    try:
        if IS_WIN:
            subprocess.check_call([
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-Command", "irm https://astral.sh/uv/install.ps1 | iex"
            ])
        else:
            subprocess.check_call(["curl", "-LSf", "https://astral.sh/uv/install.sh"], stdout=subprocess.DEVNULL)
            subprocess.check_call(["sh"], input=open("https://astral.sh/uv/install.sh").read(), text=True)
    except Exception as e:
        warn(f"uv 安装失败：{e}")
        return None

    return find_uv()


def ensure_uv() -> str:
    uv = find_uv()
    if uv:
        return uv

    uv = install_uv()
    if uv:
        info("✓ uv 安装完成")
        return uv

    die("uv 安装失败。请手动安装：https://docs.astral.sh/uv/getting-started/installation/")
    return ""  # 不会执行到这里


# ---------- venv + 依赖 ----------

def ensure_venv(uv: str) -> None:
    if PY_IN_VENV.exists():
        return

    info("创建虚拟环境 .venv/（首次约 5-30 秒，需要时会自动下载 Python）...")
    subprocess.check_call([uv, "venv", str(VENV), "--python", ">=3.10"])
    info("✓ 虚拟环境已就绪")


def test_mirror_speed(mirror_url: str, timeout: int = 3) -> float:
    """测试镜像源速度，返回响应时间（秒），失败返回无穷大。"""
    import urllib.request
    import ssl
    import time
    try:
        # 禁用 SSL 验证（某些环境证书有问题）
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        # 测试镜像源根目录
        start = time.time()
        req = urllib.request.Request(mirror_url, method='HEAD')
        urllib.request.urlopen(req, timeout=timeout, context=ctx)
        return time.time() - start
    except Exception:
        return float('inf')


def select_fastest_mirror() -> tuple[str, str]:
    """测试所有镜像源速度，返回最快的源。"""
    # 检查缓存
    cache_file = ROOT / ".mirror_cache"
    if cache_file.exists():
        try:
            cached = cache_file.read_text().strip().split('|')
            if len(cached) == 2:
                info(f"使用缓存的镜像源: {cached[1]}")
                return cached[0], cached[1]
        except Exception:
            pass

    info("正在测试镜像源速度...")
    fastest_url = None
    fastest_name = None
    fastest_time = float('inf')

    for mirror_url, mirror_name in PYPI_MIRRORS:
        speed = test_mirror_speed(mirror_url)
        if speed < fastest_time:
            fastest_time = speed
            fastest_url = mirror_url
            fastest_name = mirror_name

    if fastest_url:
        info(f"最快的镜像源: {fastest_name} ({fastest_time:.2f}s)")
        # 缓存结果
        try:
            cache_file.write_text(f"{fastest_url}|{fastest_name}")
        except Exception:
            pass
        return fastest_url, fastest_name
    
    die("所有镜像源都无法连接，请检查网络后重试")
    return "", ""


def pip_install(
    uv: str,
    packages: list[str],
    *,
    index_url: str | None = None,
    upgrade: bool = False,
) -> None:
    if not packages:
        return

    cmd = [uv, "pip", "install", "--python", str(PY_IN_VENV)]
    if upgrade:
        cmd.append("--upgrade")

    if index_url:
        cmd += ["--index-url", index_url]
    else:
        # 测试速度并选择最快的镜像源
        mirror_url, mirror_name = select_fastest_mirror()
        cmd += ["--index-url", mirror_url]

    info("接下来会看到 pip 滚动下载进度条——只要在动就是在装，不要关窗口。")
    subprocess.check_call(cmd + packages)


def packages_for_modes(modes: list[str]) -> list[str]:
    seen: dict[str, None] = {pkg: None for pkg in CORE_PACKAGES}
    for mode in modes:
        for pkg in MODE_PACKAGES.get(mode, []):
            seen[pkg] = None
    return list(seen.keys())


def wants_cuda_backend(runtime: str) -> bool:
    if runtime == "cpu":
        return False
    return shutil.which("nvidia-smi") is not None


def ensure_dependencies(uv: str, modes: list[str], install: dict, force: bool) -> None:
    packages = packages_for_modes(modes)
    sig = "|".join(sorted(packages))
    last_sig = install.get("packages_sig")

    if not force and last_sig == sig and PY_IN_VENV.exists():
        info("依赖已是最新，跳过安装")
        return

    info(f"准备安装 {len(packages)} 个 pip 包")

    # GPU 检测
    runtime = install.get("runtime", "auto")
    if wants_cuda_backend(runtime):
        info("检测到 NVIDIA GPU，安装 CUDA 版 PyTorch")
        pip_install(uv, ["torch>=2.2", "torchvision>=0.17"],
                    index_url="https://download.pytorch.org/whl/cu128",
                    upgrade=True)

    pip_install(uv, packages)

    # 把项目本身以 editable 模式装进 venv，让 uvicorn 能 import photopicker.backend
    info("注册项目包（photopicker）...")
    subprocess.check_call([uv, "pip", "install", "--python", str(PY_IN_VENV), "-e", str(ROOT)])

    install["packages_sig"] = sig
    install["modes"] = modes
    save_install(install)
    info("✓ 依赖安装完成")


def build_frontend():
    """构建前端。"""
    frontend_dir = ROOT / "frontend"
    dist_dir = frontend_dir / "dist"
    index_file = dist_dir / "index.html"

    # 如果已经构建过，跳过
    if index_file.exists():
        info("✓ 前端已构建")
        return

    # 检查是否有 Node.js
    if not shutil.which("node"):
        print()
        print("❌ 未找到 Node.js，无法构建前端页面。")
        print()
        print("  请先安装 Node.js（推荐 v18 或更新版本）：")
        print("    macOS:   brew install node")
        print("    Windows: 访问 https://nodejs.org 下载安装")
        print()
        print("  安装完成后重新双击启动脚本即可。")
        print()
        try:
            input("按回车键退出...")
        except EOFError:
            pass
        sys.exit(1)

    info("正在构建前端...")
    try:
        # 检查是否需要安装 npm 依赖
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            info("安装前端依赖（首次约 1 分钟）...")
            subprocess.run(
                ["npm", "install"],
                cwd=str(frontend_dir),
                check=True,
            )

        # 构建前端
        subprocess.run(
            ["npm", "run", "build"],
            cwd=str(frontend_dir),
            check=True,
        )
        info("✓ 前端构建完成")
    except subprocess.CalledProcessError as e:
        print()
        print(f"❌ 前端构建失败：{e}")
        print()
        print("  请手动构建前端：")
        print("    cd frontend")
        print("    npm install")
        print("    npm run build")
        print()
        try:
            input("按回车键退出...")
        except EOFError:
            pass
        sys.exit(1)


# ---------- 启动 app ----------

def check_port(port: int) -> bool:
    """Check if port is available. Returns True if available."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def find_process_on_port(port: int) -> str | None:
    """Find process name using the port."""
    try:
        if IS_WIN:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    # Get process name
                    proc_result = subprocess.run(
                        ["tasklist", "/fi", f"PID eq {pid}"],
                        capture_output=True, text=True, timeout=5
                    )
                    for proc_line in proc_result.stdout.splitlines():
                        if pid in proc_line:
                            return proc_line.split()[0]
        else:
            result = subprocess.run(
                ["lsof", "-i", f":{port}", "-t"],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                pid = result.stdout.strip().split("\n")[0]
                proc_result = subprocess.run(
                    ["ps", "-p", pid, "-o", "comm="],
                    capture_output=True, text=True, timeout=5
                )
                return proc_result.stdout.strip()
    except Exception:
        pass
    return None


def kill_port_process(port: int) -> bool:
    """Kill process using the port."""
    try:
        if IS_WIN:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    pid = line.split()[-1]
                    subprocess.run(["taskkill", "/F", "/PID", pid], timeout=5)
                    return True
        else:
            result = subprocess.run(
                ["lsof", "-i", f":{port}", "-t"],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                pid = result.stdout.strip().split("\n")[0]
                subprocess.run(["kill", "-9", pid], timeout=5)
                return True
    except Exception:
        pass
    return False


def run_app(port: int, runtime: str) -> int:
    # 检测端口状态
    if not check_port(port):
        proc_name = find_process_on_port(port)
        if proc_name and "python" in proc_name.lower():
            warn(f"端口 {port} 已被拣影服务占用")
            if sys.stdin.isatty():
                try:
                    raw = input("是否停止旧服务并重启？(y/n): ").strip().lower()
                except EOFError:
                    raw = "y"
                if raw in ("y", "yes", ""):
                    info("正在停止旧服务...")
                    kill_port_process(port)
                    import time
                    time.sleep(1)
                else:
                    warn("跳过启动，请手动停止旧服务或更换端口")
                    return 1
            else:
                info("自动停止旧服务...")
                kill_port_process(port)
                import time
                time.sleep(1)
        else:
            warn(f"端口 {port} 已被其他程序占用")
            warn("请关闭占用端口的程序，或设置环境变量 PHOTOPICKER_PORT 使用其他端口")
            return 1

    info(f"启动服务于 http://localhost:{port}")
    print()
    print("=" * 56)
    print("  服务启动后浏览器会自动打开。")
    print("  ⚠ 关闭本窗口 = 停止服务。挑完片再关。")
    print()
    print("  首次启动会加载 AI 模型（约 1-3 分钟）：")
    print("    • CLIP 语义模型（~350MB）")
    print("    • DINOv2 视觉模型（~350MB）")
    print("    • InsightFace 人脸模型（~300MB）")
    print()
    print("  看到 'Application startup complete' 后即可访问页面。")
    print("=" * 56)
    print()

    env = os.environ.copy()
    env.setdefault("HF_ENDPOINT", HF_MIRROR)

    cmd = [str(PY_IN_VENV), "-m", "uvicorn", "photopicker.backend.app:app",
           "--host", "127.0.0.1", "--port", str(port), "--reload"]

    try:
        return subprocess.call(cmd, cwd=str(PROJECT_ROOT), env=env)
    except KeyboardInterrupt:
        return 0


# ---------- 主流程 ----------

def main() -> int:
    banner("拣影 · 启动器")
    print()
    print("  本启动器会自动：选模式 → 装依赖 → 起服务")
    print("  当前已开启国内镜像加速（多源自动切换）")
    print()

    if not (ROOT / "backend" / "app.py").exists():
        die(f"未找到 app.py（期望路径：{ROOT / 'backend' / 'app.py'}）。请确认启动器放在项目根目录。")

    install = load_install()
    is_first_run = not (install.get("modes") and install.get("runtime"))

    # 步骤 1：选择模式 / 运行设备
    step(1, 3, "选择运行模式" if is_first_run else "沿用上次配置")
    if not is_first_run:
        info("（如需重新选择模式或设备，请删除 .photopicker_install.json 后重启）")
    prev_modes = install.get("modes") or []
    modes = ask_modes(prev_modes)
    install["modes"] = modes
    runtime = ask_runtime(install.get("runtime"))
    install["runtime"] = runtime
    save_install(install)

    # 步骤 2：uv + venv + 依赖
    step(2, 4, "准备 Python 环境与依赖")
    uv = ensure_uv()
    ensure_venv(uv)
    ensure_dependencies(uv, modes, install, force=False)

    # 步骤 3：构建前端
    step(3, 4, "构建前端")
    build_frontend()

    # 步骤 4：启动
    step(4, 4, "启动应用")
    port = int(os.environ.get("PHOTOPICKER_PORT", "8010"))
    rc = run_app(port, runtime)

    if rc != 0:
        warn(f"app.py 以非零状态退出（{rc}）")
        try:
            input("按回车键退出...")
        except EOFError:
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
