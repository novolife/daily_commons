# Daily Commons Wallpaper

仿 Bing 壁纸，每日从 [Wikimedia Commons 精选宽屏壁纸](https://commons.wikimedia.org/wiki/Category:Commons_featured_widescreen_desktop_backgrounds) 获取图片并设置为桌面背景。

## 功能特点

- **EXE 独立运行** - 打包成单文件，无需安装 Python
- **后台托盘** - 最小化到系统托盘，不占用任务栏
- **开机自启** - 托盘菜单一键开关
- **跨日自动更换** - 检测日期变化，新的一天自动换新图（基于日期种子随机）
- 从 800+ 张精选宽屏壁纸中选取

## 快速开始

### 方式一：使用 EXE（推荐）

1. 运行 `build.bat` 打包生成 `dist\DailyCommonsWallpaper.exe`
2. 双击 exe 启动，程序将最小化到系统托盘
3. 右键托盘图标：
   - **立即更换壁纸** - 手动换一张
   - **开机自启** - 勾选后开机自动运行
   - **退出** - 关闭程序

### 方式二：Python 运行

```bash
pip install pystray Pillow
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
pip install pystray Pillow pyinstaller
# 若提示 typing 冲突，先执行: pip uninstall typing
pyinstaller --clean build.spec
```

生成的无控制台 exe 位于 `dist\DailyCommonsWallpaper.exe`。

## 文件说明

| 文件 | 说明 |
|------|------|
| `wallpaper.py` | 主程序 |
| `build.spec` | PyInstaller 配置 |
| `build.bat` | 一键打包脚本 |
| `run_wallpaper.bat` | Python 快速运行 |
| `%USERPROFILE%\.daily_commons_wallpaper\` | 壁纸缓存目录 |

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--tray` | 后台托盘模式（默认） |
| `--once` | 仅运行一次后退出 |
| `-r, --random` | 随机选择（配合 --once） |
| `-n, --count` | 获取图片数量，默认 200 |

## 图片来源

图片来自 [Wikimedia Commons](https://commons.wikimedia.org/)，遵循各图片的原始许可协议（多为 CC 系列）。
