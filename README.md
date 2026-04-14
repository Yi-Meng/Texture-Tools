# Textures Tool

## 是什么

一个面向技术美术的批量图片尺寸处理工具，用于把 UI 或贴图资源整理为 2 的整数次幂尺寸。

支持两种处理方式：

- `pad`：保持原始内容尺寸不变，只扩展画布
- `scale`：直接把内容缩放到目标尺寸

支持命令行和 Tkinter GUI。

扫描文件夹时会自动跳过：

- Unity `.meta` 文件
- 所有非图片文件

当前支持的图片类型：

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

macOS：

```bash
chmod +x build_macos.sh
./build_macos.sh
```
