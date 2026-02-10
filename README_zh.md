# Daily Commons Wallpaper

[![Build](https://github.com/novolife/daily_commons/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/novolife/daily_commons/actions)
[![Version](https://img.shields.io/badge/version-1.0.5-blue.svg)](https://github.com/novolife/daily_commons/releases)
[![Download](https://img.shields.io/badge/download-latest-green.svg)](https://github.com/novolife/daily_commons/releases/latest)

**Other languages:** [English (README.md)](README.md)

---

仿 Bing 壁纸，每日从 [Wikimedia Commons 精选宽屏壁纸](https://commons.wikimedia.org/wiki/Category:Commons_featured_widescreen_desktop_backgrounds) 获取图片并设置为桌面背景。

## 功能特点

- **EXE 独立运行** - 打包成单文件，无需安装 Python
- **后台托盘** - 最小化到系统托盘，不占用任务栏
- **开机自启** - 托盘菜单一键开关
- **跨日自动更换** - 检测日期变化，新的一天自动换新图（基于日期种子）
- **分辨率过滤** - 仅选取 ≥1920×1080 的图片
- **多语言** - 根据系统语言显示（英语、简体中文）
- 从 800+ 张精选宽屏壁纸中选取

## 快速开始

### 方式一：使用 EXE（推荐）

**[下载最新版本](https://github.com/novolife/daily_commons/releases/latest)** · 或本地打包：

1. 运行 `build.bat` 打包生成 `dist\DailyCommonsWallpaper-版本号.exe`
2. 双击 exe 启动，程序将最小化到系统托盘
3. 右键托盘图标：
   - **立即更换壁纸** - 手动换一张
   - **开机自启** - 勾选后开机自动运行
   - **当前壁纸信息** - 显示标题、作者、许可
   - **在 Commons 查看** - 在 Wikimedia Commons 打开当前图片
   - **打开缓存文件夹** - 打开壁纸缓存目录
   - **退出** - 关闭程序

**托盘图标不显示？** ① 点击任务栏右下角 `^` 查看隐藏图标；② 设置 → 个性化 → 任务栏 → 其他系统托盘图标，开启本程序；③ **GitHub 下载的 exe**：右键 → 属性 → 勾选「解除锁定」→ 确定（消除网络来源标记）。

### 无法运行？被杀毒软件拦截？

若 exe 双击无反应或被 Windows Defender / 杀毒软件删除：

1. **信任/排除**：将 exe 添加到杀毒软件白名单，或从 Windows 安全中心 → 病毒和威胁防护 → 允许的应用 中恢复
2. **Python 方式运行**：若 exe 无法使用，可直接用 Python 运行：`python wallpaper.py --tray`（需先 `pip install infi.systray pystray Pillow`）
3. **本地重新打包**：运行 `build.bat` 自行打包，本仓库已禁用 UPX 压缩以减少误报

```bash
pip install infi.systray pystray Pillow
python wallpaper.py          # 托盘模式
python wallpaper.py --once   # 仅运行一次
python wallpaper.py --once -r  # 随机一张后退出
```

## 跨日逻辑

- 程序每 60 秒检测一次日期
- 当检测到日期变化（跨日）时，自动获取新图片并设置壁纸
- 同一天内使用相同种子，保证图片一致；新的一天使用新种子，获得新图片

## 打包说明

```bash
pip install infi.systray pystray Pillow pyinstaller
# 若提示 typing 冲突，先执行: pip uninstall typing
pyinstaller --clean build.spec
```

生成的无控制台 exe 位于 `dist\DailyCommonsWallpaper.exe`。

## 项目结构

| 文件 | 说明 |
|------|------|
| `wallpaper.py` | 主入口 |
| `core.py` | 获取、下载、更新逻辑 |
| `tray.py` | 系统托盘 |
| `config.py` | 配置常量 |
| `i18n/` | 语言文件（en.json, zh_CN.json） |
| `%USERPROFILE%\.daily_commons_wallpaper\` | 壁纸缓存目录 |

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--tray` | 后台托盘模式（默认） |
| `--once` | 仅运行一次后退出 |
| `-r, --random` | 随机选择（配合 --once） |
| `-n, --count` | 获取图片数量，默认 500 |

## 图片来源

图片来自 [Wikimedia Commons](https://commons.wikimedia.org/)，遵循各图片的原始许可协议（多为 CC 系列）。

## License

MIT License - 详见 [LICENSE](LICENSE) 文件。
