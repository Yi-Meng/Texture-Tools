from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core import DEFAULT_CONFIG, ProcessFailure, ProcessResult, process_batch


MODE_LABELS = {"补边": "pad", "缩放": "scale"}
MODE_VALUES = list(MODE_LABELS.keys())

ROUNDING_LABELS = {"向上取整": "up", "最近值": "nearest", "向下取整": "down"}
ROUNDING_VALUES = list(ROUNDING_LABELS.keys())

ANCHOR_LABELS = {
    "居中": "center",
    "左上": "top_left",
    "上方": "top",
    "右上": "top_right",
    "左侧": "left",
    "右侧": "right",
    "左下": "bottom_left",
    "下方": "bottom",
    "右下": "bottom_right",
}
ANCHOR_VALUES = list(ANCHOR_LABELS.keys())


class TextureResizeApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Textures Tool")
        self.root.geometry("960x720")
        self.root.minsize(880, 640)

        self.input_paths: list[str] = []
        self.log_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None

        self.output_dir_var = tk.StringVar(value="")
        self.mode_var = tk.StringVar(value=self._label_for(DEFAULT_CONFIG["mode"], MODE_LABELS))
        self.rounding_var = tk.StringVar(value=self._label_for(DEFAULT_CONFIG["rounding"], ROUNDING_LABELS))
        self.anchor_var = tk.StringVar(value=self._label_for(DEFAULT_CONFIG["anchor"], ANCHOR_LABELS))
        self.background_var = tk.StringVar(value="0,0,0,0")
        self.overwrite_var = tk.BooleanVar(value=DEFAULT_CONFIG["overwrite"])
        self.only_shrink_var = tk.BooleanVar(value=DEFAULT_CONFIG["only_shrink"])
        self.limit_smaller_var = tk.BooleanVar(value=DEFAULT_CONFIG["limit_smaller"])
        self.suffix_var = tk.StringVar(value=DEFAULT_CONFIG["suffix"])

        self.form_widgets: list[tk.Widget] = []

        self._build_ui()
        self._update_output_state()
        self.root.after(100, self._drain_log_queue)

    @staticmethod
    def _label_for(value: str, mapping: dict[str, str]) -> str:
        return next(label for label, internal in mapping.items() if internal == value)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(3, weight=1)

        input_frame = ttk.LabelFrame(container, text="输入源", padding=10)
        input_frame.grid(row=0, column=0, sticky="nsew")
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1)

        self.input_listbox = tk.Listbox(input_frame, height=8, selectmode=tk.EXTENDED)
        self.input_listbox.grid(row=0, column=0, sticky="nsew")
        self.form_widgets.append(self.input_listbox)

        input_scrollbar = ttk.Scrollbar(input_frame, orient="vertical", command=self.input_listbox.yview)
        input_scrollbar.grid(row=0, column=1, sticky="ns")
        self.input_listbox.configure(yscrollcommand=input_scrollbar.set)

        input_button_row = ttk.Frame(input_frame)
        input_button_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        for column in range(3):
            input_button_row.columnconfigure(column, weight=1)

        add_file_button = ttk.Button(input_button_row, text="添加文件", command=self.add_files)
        add_file_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.form_widgets.append(add_file_button)

        add_folder_button = ttk.Button(input_button_row, text="添加文件夹", command=self.add_folder)
        add_folder_button.grid(row=0, column=1, sticky="ew", padx=3)
        self.form_widgets.append(add_folder_button)

        remove_button = ttk.Button(input_button_row, text="移除选中", command=self.remove_selected)
        remove_button.grid(row=0, column=2, sticky="ew", padx=(6, 0))
        self.form_widgets.append(remove_button)

        output_frame = ttk.LabelFrame(container, text="输出设置", padding=10)
        output_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        output_frame.columnconfigure(1, weight=1)

        ttk.Label(output_frame, text="输出目录").grid(row=0, column=0, sticky="w")
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_dir_var)
        self.output_entry.grid(row=0, column=1, sticky="ew", padx=(8, 8))
        self.form_widgets.append(self.output_entry)

        self.output_button = ttk.Button(output_frame, text="浏览", command=self.choose_output_dir)
        self.output_button.grid(row=0, column=2, sticky="ew")
        self.form_widgets.append(self.output_button)

        options_frame = ttk.LabelFrame(container, text="处理参数", padding=10)
        options_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        for column in range(4):
            options_frame.columnconfigure(column, weight=1)

        ttk.Label(options_frame, text="模式").grid(row=0, column=0, sticky="w")
        mode_combo = ttk.Combobox(options_frame, textvariable=self.mode_var, values=MODE_VALUES, state="readonly")
        mode_combo.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 8))
        self.form_widgets.append(mode_combo)

        ttk.Label(options_frame, text="取整").grid(row=0, column=1, sticky="w")
        rounding_combo = ttk.Combobox(options_frame, textvariable=self.rounding_var, values=ROUNDING_VALUES, state="readonly")
        rounding_combo.grid(row=1, column=1, sticky="ew", padx=8, pady=(4, 8))
        self.form_widgets.append(rounding_combo)

        ttk.Label(options_frame, text="锚点").grid(row=0, column=2, sticky="w")
        anchor_combo = ttk.Combobox(options_frame, textvariable=self.anchor_var, values=ANCHOR_VALUES, state="readonly")
        anchor_combo.grid(row=1, column=2, sticky="ew", padx=8, pady=(4, 8))
        self.form_widgets.append(anchor_combo)

        ttk.Label(options_frame, text="后缀").grid(row=0, column=3, sticky="w")
        suffix_entry = ttk.Entry(options_frame, textvariable=self.suffix_var)
        suffix_entry.grid(row=1, column=3, sticky="ew", padx=(8, 0), pady=(4, 8))
        self.form_widgets.append(suffix_entry)

        ttk.Label(options_frame, text="背景 RGBA").grid(row=2, column=0, sticky="w")
        background_entry = ttk.Entry(options_frame, textvariable=self.background_var)
        background_entry.grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))
        self.form_widgets.append(background_entry)

        overwrite_check = ttk.Checkbutton(options_frame, text="覆盖原图", variable=self.overwrite_var, command=self._update_output_state)
        overwrite_check.grid(row=3, column=1, sticky="w", padx=8, pady=(4, 0))
        self.form_widgets.append(overwrite_check)

        only_shrink_check = ttk.Checkbutton(options_frame, text="只缩小", variable=self.only_shrink_var)
        only_shrink_check.grid(row=3, column=2, sticky="w", padx=8, pady=(4, 0))
        self.form_widgets.append(only_shrink_check)

        limit_smaller_check = ttk.Checkbutton(options_frame, text="禁止目标尺寸小于原图", variable=self.limit_smaller_var)
        limit_smaller_check.grid(row=3, column=3, sticky="w", padx=(8, 0), pady=(4, 0))
        self.form_widgets.append(limit_smaller_check)

        action_row = ttk.Frame(container)
        action_row.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        action_row.columnconfigure(0, weight=1)
        action_row.rowconfigure(1, weight=1)

        self.start_button = ttk.Button(action_row, text="开始处理", command=self.start_processing)
        self.start_button.grid(row=0, column=0, sticky="e", pady=(0, 8))
        self.form_widgets.append(self.start_button)

        log_frame = ttk.LabelFrame(action_row, text="日志", padding=10)
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")

        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

    def add_files(self) -> None:
        selected = filedialog.askopenfilenames(
            title="选择图片文件",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.tga *.bmp *.webp"), ("All Files", "*.*")],
        )
        self._append_inputs(selected)

    def add_folder(self) -> None:
        selected = filedialog.askdirectory(title="选择文件夹")
        if selected:
            self._append_inputs([selected])

    def remove_selected(self) -> None:
        indices = list(self.input_listbox.curselection())
        for index in reversed(indices):
            del self.input_paths[index]
            self.input_listbox.delete(index)

    def choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="选择输出目录")
        if selected:
            self.output_dir_var.set(selected)

    def _append_inputs(self, paths: tuple[str, ...] | list[str]) -> None:
        seen = set(self.input_paths)
        for path in paths:
            normalized = str(Path(path).resolve())
            if normalized in seen:
                continue
            seen.add(normalized)
            self.input_paths.append(normalized)
            self.input_listbox.insert(tk.END, normalized)

    def _update_output_state(self) -> None:
        state = "disabled" if self.overwrite_var.get() else "normal"
        self.output_entry.configure(state=state)
        self.output_button.configure(state=state)

    def _set_form_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        readonly_state = "readonly" if enabled else "disabled"

        for widget in self.form_widgets:
            if isinstance(widget, ttk.Combobox):
                widget.configure(state=readonly_state)
            elif widget in (self.output_entry,) and self.overwrite_var.get() and enabled:
                widget.configure(state="disabled")
            elif widget in (self.output_button,) and self.overwrite_var.get() and enabled:
                widget.configure(state="disabled")
            else:
                widget.configure(state=state)

        self._update_output_state()

    def _parse_background(self) -> list[int]:
        raw = [part.strip() for part in self.background_var.get().split(",")]
        if len(raw) != 4:
            raise ValueError("背景颜色必须是 r,g,b,a 四个值。")

        values = []
        for item in raw:
            value = int(item)
            if value < 0 or value > 255:
                raise ValueError("背景颜色每个通道必须在 0-255 之间。")
            values.append(value)
        return values

    def _build_config(self) -> dict:
        return {
            "mode": MODE_LABELS[self.mode_var.get()],
            "rounding": ROUNDING_LABELS[self.rounding_var.get()],
            "background": self._parse_background(),
            "anchor": ANCHOR_LABELS[self.anchor_var.get()],
            "overwrite": self.overwrite_var.get(),
            "only_shrink": self.only_shrink_var.get(),
            "limit_smaller": self.limit_smaller_var.get(),
            "suffix": self.suffix_var.get(),
        }

    def start_processing(self) -> None:
        if not self.input_paths:
            messagebox.showerror("缺少输入", "请先添加至少一个文件或文件夹。")
            return

        try:
            config = self._build_config()
        except ValueError as exc:
            messagebox.showerror("参数错误", f"{exc}\n格式示例: 0,0,0,0")
            return

        output_dir = None if self.overwrite_var.get() else self.output_dir_var.get().strip() or None
        self._set_form_enabled(False)
        self._clear_log()
        self._append_log("开始处理...")

        self.worker = threading.Thread(target=self._run_batch, args=(list(self.input_paths), config, output_dir), daemon=True)
        self.worker.start()

    def _run_batch(self, inputs: list[str], config: dict, output_dir: str | None) -> None:
        def progress(event: str, payload: object) -> None:
            self.log_queue.put((event, payload))

        try:
            results, failures = process_batch(inputs, config, output_dir=output_dir, progress_callback=progress)
            self.log_queue.put(("done", {"results": results, "failures": failures}))
        except Exception as exc:  # noqa: BLE001
            self.log_queue.put(("fatal", str(exc)))

    def _drain_log_queue(self) -> None:
        while True:
            try:
                event, payload = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if event == "scan":
                data = payload
                self._append_log(f"[{data['index']}/{data['total']}] 扫描 {data['path']}")
            elif event == "skipped":
                data = payload
                self._append_log(f"跳过已生成文件: {data['path']}")
            elif event == "processed":
                result = payload
                self._append_log(
                    f"完成: {result.source.name} "
                    f"{result.original_size[0]}x{result.original_size[1]} -> "
                    f"{result.final_size[0]}x{result.final_size[1]} [{result.action}]"
                )
                self._append_log(f"输出: {result.target}")
            elif event == "failed":
                failure = payload
                self._append_log(f"失败: {failure.source} -> {failure.error}")
            elif event == "done":
                results: list[ProcessResult] = payload["results"]
                failures: list[ProcessFailure] = payload["failures"]
                self._append_log("")
                self._append_log(f"处理结束。成功 {len(results)} 个，失败 {len(failures)} 个。")
                self._set_form_enabled(True)
                self.worker = None
            elif event == "fatal":
                self._append_log(f"任务终止: {payload}")
                messagebox.showerror("处理失败", str(payload))
                self._set_form_enabled(True)
                self.worker = None

        self.root.after(100, self._drain_log_queue)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")


def main() -> int:
    root = tk.Tk()
    TextureResizeApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
