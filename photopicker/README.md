# 拣影 📸

[![CI](https://github.com/zhengbiaox/jianying/actions/workflows/ci.yml/badge.svg)](https://github.com/zhengbiaox/jianying/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)

本地智能选片工具，帮你从海量照片中快速挑选最佳照片。

## ✨ 功能特性

- 🎯 **智能分组** - 按场景相似度自动分组，PK 时只比较相似照片
- 🔍 **质量检测** - 自动识别模糊、过曝、闭眼等技术问题
- ⚔️ **PK选片** - 两两对比，快速选出最佳照片
- 👤 **人物识别** - 自动识别照片中的人物，按人物分组
- 📁 **RAW支持** - 支持 RAW 文件配对导出
- 🎬 **暂存功能** - 不确定的照片可暂存，最后统一处理
- 🖥️ **跨平台** - 支持 macOS 和 Windows

## 🚀 快速开始

### 前置要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 无需手动安装 | 启动脚本会通过 uv 自动下载 |
| Node.js | v18+ | 用于构建前端，[官网下载](https://nodejs.org) |

### 方式一：一键启动（推荐）

**macOS:**
```bash
双击 start_mac.command
```

**Windows:**
```bash
双击 start_windows.bat
```

首次启动会自动安装 Python 依赖并构建前端，需要联网，约 5-15 分钟。

### 方式二：手动启动

```bash
# 安装 uv（Python 工具链管理器）
pip install uv

# 安装依赖
uv pip install -r requirements.txt

# 构建前端
cd frontend && npm install && npm run build && cd ..

# 启动服务
python -m uvicorn photopicker.backend.app:app --port 8010
```

打开浏览器访问 http://localhost:8010

## 📁 项目结构

```
photopicker/
├── backend/
│   ├── app.py          # FastAPI 主入口
│   ├── grouper.py      # 分组算法
│   ├── detector.py     # 质量检测
│   ├── vision.py       # AI模型管理
│   ├── exporter.py     # 导出逻辑
│   └── models.py       # 数据模型
├── frontend/
│   └── src/            # Vue 3 前端
├── scripts/
│   └── launcher.py     # 启动器脚本
├── start_mac.command   # macOS 启动脚本
├── start_windows.bat   # Windows 启动脚本
└── requirements.txt    # Python 依赖
```

## ⌨️ 快捷键

| 操作 | 快捷键 |
|---|---|
| 选中左边 | `←` |
| 选中右边 | `→` |
| 两张都选 | `↑` |
| 两张都不要 | `↓` |
| 人物统计 | `Space` |
| 撤销 | `Shift + Z` |

## 🔄 工作流程

```
导入 → 技术筛选 → PK选片 → 确认导出
```

1. **导入** - 选择照片文件夹，设置筛选强度
2. **技术筛选** - 自动检测废片，可捞回误杀
3. **PK选片** - 两两对比选择，支持暂存
4. **确认导出** - 人物命名，按人物/场景分文件夹导出

## 🔬 技术算法

### 质量检测（7种算法）

| 算法 | 用途 |
|------|------|
| Tenengrad | 模糊检测 |
| FFT 高频比 | 模糊检测 |
| Marziliano 边缘宽度 | 模糊检测 |
| 9宫格曝光分析 | 过曝/欠曝检测 |
| 霍夫变换 | 水平线倾斜检测 |
| 显著性图 | 主体锐度保护 |
| 梯度方差 | 运动模糊检测 |

### 人脸检测

- InsightFace 人脸检测与闭眼识别
- MediaPipe 降级方案（无 GPU 时）

### 分组算法（多信号融合）

| 信号 | 权重 | 说明 |
|------|------|------|
| 感知哈希 | 20% | pHash + dHash + wHash + aHash |
| 色彩直方图 | 10% | HSV 3×3 分块 |
| 拍摄时间 | 15% | 指数衰减相似度 |
| 文件名 | 8% | 连拍序列检测 |
| CLIP 语义 | 20% | 图像内容理解 |
| DINOv2 视觉 | 20% | 视觉特征提取 |

### 人脸聚类

- InsightFace 提取人脸特征向量
- cosine 相似度 Union-Find 聚类
- 相似度阈值: 0.6

### AI 模型（可选，自动降级）

| 模型 | 用途 | 大小 |
|------|------|------|
| CLIP ViT-B-32 | 语义理解 | ~350MB |
| DINOv2-base | 视觉特征 | ~350MB |
| InsightFace buffalo_sc | 人脸检测 | ~300MB |

模型加载失败时自动降级到纯算法模式。

## 🛠️ 技术栈

- **后端**: Python / FastAPI / OpenCV / PyTorch
- **前端**: Vue 3 / Vite
- **AI模型**: CLIP / DINOv2 / InsightFace（可选，自动降级）

## 📦 依赖镜像

启动脚本会自动使用国内镜像源：
- pip: 阿里云 / 清华 / 中科大
- HuggingFace: hf-mirror.com

## 📄 License

MIT License
