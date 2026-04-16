# Textures Tool

## 是什么
一个面向技术美术的批量图片处理工具，用来把 UI 图或贴图整理为 2 的整数次幂尺寸。

支持两种处理方式：
- `pad`：保持原内容尺寸不变，只扩展画布。
- `scale`：直接把内容缩放到目标尺寸。

支持命令行和 Tkinter GUI。

扫描文件夹时会自动跳过：
- Unity `.meta` 文件
- 所有非图片文件

当前支持的图片格式：
- `.png`
- `.jpg`
- `.jpeg`
- `.tga`
- `.bmp`
- `.webp`

## 怎么用
先安装依赖：

```bash
pip install -r requirements.txt
```

### GUI

直接运行：

```bash
python texture_resize_gui.py
```

Windows：

```powershell
run_texture_tool_gui.bat
```

macOS：

```bash
chmod +x launchers/run_texture_tool_gui.command
./launchers/run_texture_tool_gui.command
```

### CLI

处理单个文件：

```bash
python texture_resize_tool.py path/to/image.png
```

处理整个文件夹：

```bash
python texture_resize_tool.py path/to/folder
```

指定配置：

```bash
python texture_resize_tool.py path/to/folder --config config/config.example.json
```

输出到指定目录：

```bash
python texture_resize_tool.py path/to/folder --output-dir path/to/output
```

### 打包

Windows：

```powershell
./build_windows.ps1
```

macOS 基础打包：

```bash
chmod +x build_macos.sh
./build_macos.sh
```

macOS 正式发布包（签名 + notarization + Release 产物）：

```bash
export APPLE_SIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)"
export APPLE_NOTARY_PROFILE="your-notary-profile"
./build_macos.sh --release
```

正式发布产物会输出到：

```text
release_assets/
```
