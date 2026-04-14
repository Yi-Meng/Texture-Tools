# Textures Tool

一个面向技术美术的批量图片尺寸整理工具，优先解决 UI 图像分辨率不是 2 的整数次幂的问题。

## 项目结构

```text
TexturesTool/
├─ config/                   # 示例配置
├─ launchers/                # 用户启动脚本
├─ src/textures_tool/        # 真正的源码包
├─ scripts/                  # 构建脚本
├─ texture_resize_gui.py     # GUI 入口
├─ texture_resize_tool.py    # CLI 入口
├─ run_texture_tool*.bat     # 根目录兼容启动入口
├─ run_texture_tool*.command # 根目录兼容启动入口
└─ README.md
```

说明：

- 根目录入口文件保留，是为了兼容直接运行和打包
- 主要逻辑已经收进 `src/textures_tool`
- 实际启动脚本已经收进 `launchers/`
- 示例配置已经收进 `config/`
- `build`、`dist`、`spec` 都属于构建产物，已加入 `.gitignore`

## 当前功能

- 批量扫描文件或文件夹
- 自动把宽高调整到 2 的整数次幂
- 支持两种策略
  - `pad`：保持原始内容尺寸不变，只扩展画布
  - `scale`：直接把内容缩放到目标尺寸
- 支持命令行和 Tkinter GUI
- Windows 可通过 `.bat` 启动
- macOS 可通过 `.command` 启动

## 安装

```bash
pip install -r requirements.txt
```

如果只是使用已经打包好的程序，目标电脑不需要安装 Python。

## 无 Python 环境分发

项目现在支持准备可直接运行的打包产物：

- Windows：`.exe`
- macOS：`.app` 和 CLI 可执行文件

构建方式：

```powershell
./build_windows.ps1
```

macOS 构建方式：

```bash
chmod +x build_macos.sh
./build_macos.sh
```

构建完成后会在 `dist` 目录生成：

- `TexturesTool.exe`：GUI 版本，适合美术直接双击使用
- `TexturesToolCLI.exe`：命令行版本，适合流水线或批处理
- `TexturesTool.app`：macOS GUI 版本
- `TexturesToolCLI`：macOS CLI 版本

如果只想打 CLI：

```powershell
./build_windows.ps1 -CliOnly
```

```bash
./build_macos.sh --cli-only
```

说明：

- 打包后的 Windows 程序自带 Python 运行环境，不依赖目标机器安装 Python
- 打包后的 macOS 程序也不依赖目标机器安装 Python
- macOS 打包需要在 Mac 上执行，不能在 Windows 上直接产出 `.app`
- 未签名的 macOS `.app` 可能会被系统拦截，内部使用时通常可通过“右键打开”或安全设置放行

## GUI 使用

启动 GUI：

```bash
python texture_resize_gui.py
```

Windows 下也可以直接双击 `run_texture_tool_gui.bat`。
macOS 下可以双击 `run_texture_tool_gui.command`，或在终端执行：

```bash
chmod +x launchers/run_texture_tool_gui.command
./launchers/run_texture_tool_gui.command
```

第一版 GUI 适合美术手动操作，支持：

- 添加文件和文件夹
- 选择输出目录
- 设置模式、取整、锚点、背景 RGBA、后缀
- 选择是否覆盖原图、只缩小、禁止目标尺寸小于原图
- 查看逐文件处理日志

当前 GUI 不支持：

- 拖拽导入
- 缩略图预览
- 保存和读取 GUI 预设

## CLI 使用

CLI 适合流水线、批处理或拖拽调用。

处理单个文件：

```bash
python texture_resize_tool.py C:\temp\ui_button.png
```

处理整个文件夹：

```bash
python texture_resize_tool.py C:\temp\ui_export
```

指定配置：

```bash
python texture_resize_tool.py C:\temp\ui_export --config config/config.example.json
```

输出到指定目录：

```bash
python texture_resize_tool.py C:\temp\ui_export --output-dir C:\temp\ui_export_pot
```

Windows 下也可以把文件或文件夹拖到 `run_texture_tool.bat` 上执行。
macOS 下可以执行：

```bash
chmod +x run_texture_tool.command
./run_texture_tool.command /Users/you/ui_export
```

## macOS 说明

- 脚本优先使用 `python3`，找不到时才回退到 `python`
- 首次运行 `.command` 可能需要先执行一次 `chmod +x`
- 如果 macOS 阻止打开脚本，可在“系统设置 -> 隐私与安全性”里允许执行

## 配置说明

`config/config.example.json` 示例：

```json
{
  "mode": "pad",
  "rounding": "up",
  "background": [0, 0, 0, 0],
  "resample": "lanczos",
  "anchor": "center",
  "limit_smaller": false,
  "only_shrink": false,
  "overwrite": false,
  "suffix": "_pot",
  "output_dir": "",
  "file_types": [".png", ".jpg", ".jpeg", ".tga", ".bmp", ".webp"]
}
```

关键字段：

- `mode`：`pad` 适合 UI 图，`scale` 适合允许重采样的贴图
- `rounding`：支持 `up`、`nearest`、`down`
- `background`：填充背景色，RGBA 数组
- `anchor`：控制原图在新画布中的对齐方式，例如 `center`、`top_left`、`bottom_right`
- `suffix`：输出文件名后缀
- `output_dir`：输出目录，空字符串表示输出到原图同目录

## 推荐规则

对于 UI 图片，通常建议：

- 默认使用 `pad`
- 默认使用 `rounding = up`
- 背景使用透明 `[0, 0, 0, 0]`
- 输出到单独目录，避免覆盖原图

这样更接近“保留设计内容，只补齐贴图规格”的需求。
