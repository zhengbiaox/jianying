# 拣影 📸

本地智能选片工具

## ✨ 功能特性

- 🎯 **智能分组** -
- 🔍 **质量检测** - 
- ⚔️ **PK选片** - 
- 🎬 **进度持久化** - 
- 📁 **RAW支持** - 
- 🖥️ **跨平台** -

## 🚀 快速开始

### 方式一：一键启动（推荐）

**macOS:**
- 双击 `start_mac.command`

**Windows:**
- 双击 `start_windows.bat`

### 方式二：手动启动

```bash
# 安装依赖
pip install -r requirements.txt

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
| 暂缓（跳过） | `↓` |
| 撤销 | `Shift + Z` |

## 🛠️ 技术栈

- **后端**: Python / FastAPI / OpenCV / PyTorch
- **前端**: Vue 3 / Vite
- **AI模型**: CLIP / DINOv2 / InsightFace（可选，自动降级）

## 📄 License

MIT License
