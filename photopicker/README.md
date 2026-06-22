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

### 方式一：一键启动（推荐）

**macOS:**
```bash
双击 start_mac.command
```

**Windows:**
```bash
双击 start_windows.bat
```

首次启动会自动安装依赖，需要联网。

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
