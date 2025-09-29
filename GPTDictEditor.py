# #####################################################################
# 1. 依赖检查
# #####################################################################
import sys
try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    print("错误：缺少 tkinter 包。")
    print("tkinter 通常是 Python 的标准组成部分。请确保Python安装完整。")
    print("请尝试运行 pip install tk")
    sys.exit(1)

try:
    import toml
except ImportError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("缺少依赖", "错误：缺少 'toml' 包。\n\n请在命令行运行以下命令进行安装：\npip install toml")
    sys.exit(1)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("缺少依赖", "错误: 缺少 'tkinterdnd2' 包。\n此包用于实现拖放文件功能。\n\n请在命令行运行以下命令进行安装:\npip install tkinterdnd2")
    sys.exit(1)

try:
    from tkhtmlview import HTMLScrolledText
    import markdown
except ImportError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("缺少依赖", "错误: 缺少 'tkhtmlview' 或 'markdown' 包。\n这些包用于显示格式化的帮助信息。\n\n请在命令行运行以下命令进行安装:\npip install tkhtmlview markdown")
    sys.exit(1)

# #####################################################################
# 2. 导入其他必要的模块
# #####################################################################
from tkinter import ttk, filedialog, scrolledtext
import json
import os
import re
import webbrowser
import tkinter.font as tkFont
from typing import Optional, List, Dict, Any, Tuple

# #####################################################################
# 3. 全局常量定义
# #####################################################################
APP_VERSION = "v1.1.1"
HIGHLIGHT_DELAY_MS = 250  # 语法高亮延迟时间

# 统一管理格式定义，方便扩展
FORMAT_DEFINITIONS = {
    "AiNiee_JSON": {"name": "AiNiee/LinguaGacha JSON格式", "ext": ".json"},
    "GPPGUI_TOML": {"name": "GalTranslPP GUI TOML格式", "ext": ".toml"},
    "GPPCLI_TOML": {"name": "GalTranslPP CLI TOML格式", "ext": ".toml"},
    "GalTransl_TSV": {"name": "GalTransl TSV格式", "ext": ".txt"},
}


# #####################################################################
# 4. 带行号的自定义编辑器组件
# #####################################################################
class EditorWithLineNumbers(tk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master)
        
        self.text_font = kwargs.get('font', ("Consolas", 10))
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.linenumbers = tk.Canvas(self, width=40, background="#f0f0f0", highlightthickness=0)
        self.linenumbers.grid(row=0, column=0, sticky="ns")

        self.vbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.yview)
        self.vbar.grid(row=0, column=2, sticky="ns")
        
        self.hbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL)
        self.hbar.grid(row=1, column=1, sticky="ew")

        self.text = tk.Text(self, undo=True, wrap=tk.NONE, *args, **kwargs)
        self.text.grid(row=0, column=1, sticky="nsew")
        
        self.text.config(yscrollcommand=self.on_text_scroll, xscrollcommand=self.hbar.set)
        self.hbar.config(command=self.text.xview)

        # 绑定 <<Modified>> 事件来追踪变化
        self.text.bind("<<Modified>>", self._on_change_proxy)
        self.text.bind("<Configure>", self._on_change_proxy)

        self._redraw_job = None
        self.is_modified_flag = False

    def on_text_scroll(self, first, last):
        self.vbar.set(first, last)
        self.linenumbers.yview_moveto(first)
        self.redraw_line_numbers()

    def yview(self, *args):
        self.text.yview(*args)
        self.linenumbers.yview(*args)
        self.redraw_line_numbers()
        return "break"

    def _on_change_proxy(self, event=None):
        if self.text.edit_modified():
            self.is_modified_flag = True
            self.text.edit_modified(False) # 必须重置，否则事件不会再次触发

        # 延迟重绘行号以优化性能
        if self._redraw_job:
            self.after_cancel(self._redraw_job)
        self._redraw_job = self.after(50, self.redraw_line_numbers)

    def redraw_line_numbers(self):
        self.linenumbers.delete("all")
        try:
            total_lines_str = self.text.index('end-1c').split('.')[0]
            line_count = int(total_lines_str) if total_lines_str else 1
            new_width = 25 + len(total_lines_str) * 8
            if self.linenumbers.winfo_width() != new_width:
                self.linenumbers.config(width=new_width)

            current_line_num = self.text.index(tk.INSERT).split('.')[0]
            
            i = self.text.index("@0,0")
            while True:
                dline = self.text.dlineinfo(i)
                if dline is None: break
                
                y = dline[1]
                linenum_str = i.split('.')[0]
                color = "#1e1e1e" if linenum_str == current_line_num else "#858585"
                self.linenumbers.create_text(new_width - 8, y, anchor=tk.NE, text=linenum_str, fill=color, font=self.text_font)
                i = self.text.index(f"{i}+1line")
        except (tk.TclError, ValueError):
            pass

    def get_content(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set_content(self, content: str, reset_modified_flag: bool = True):
        is_disabled = self.text.cget("state") == tk.DISABLED
        if is_disabled: self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        if reset_modified_flag:
            self.text.edit_reset()
            self.is_modified_flag = False
        if is_disabled: self.text.config(state=tk.DISABLED)

    def clear(self):
        self.set_content("", reset_modified_flag=True)

    def config(self, cnf=None, **kw):
        all_options = (cnf or {}).copy()
        all_options.update(kw)
        text_keys = tk.Text().keys()
        text_kw = {k: v for k, v in all_options.items() if k in text_keys}
        frame_kw = {k: v for k, v in all_options.items() if k not in text_keys}
        if 'font' in text_kw: self.text_font = text_kw['font']
        super().config(**frame_kw)
        if text_kw: self.text.config(**text_kw)

    def __getattr__(self, name):
        try:
            return getattr(self.text, name)
        except AttributeError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


# #####################################################################
# 5. 对话框类 (FindReplaceDialog, GoToLineDialog)
# #####################################################################
class FindReplaceDialog(tk.Toplevel):
    def __init__(self, master, target_widget, app_instance):
        super().__init__(master)
        self.transient(master)
        self.title("查找与替换（仅限输入框）")
        self.target = target_widget
        self.app = app_instance
        self.master = master
        self.match_len_var = tk.StringVar()
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.close_dialog)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(main_frame, text="查找:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.find_entry = ttk.Entry(main_frame, width=40)
        self.find_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.find_entry.focus_set()

        ttk.Label(main_frame, text="替换:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.replace_entry = ttk.Entry(main_frame, width=40)
        self.replace_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        option_frame = ttk.Frame(main_frame)
        option_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)
        self.case_var = tk.BooleanVar()
        ttk.Checkbutton(option_frame, text="区分大小写", variable=self.case_var).pack(side=tk.LEFT, padx=5)
        self.regex_var = tk.BooleanVar()
        ttk.Checkbutton(option_frame, text="正则表达式", variable=self.regex_var).pack(side=tk.LEFT, padx=5)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="查找上一个", command=self.find_previous).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="查找下一个", command=self.find_next).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="替换", command=self.replace).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="替换全部", command=self.replace_all).pack(side=tk.LEFT, padx=5)
    
    def _perform_find(self, backwards=False):
        self.target.tag_remove('found', '1.0', tk.END)
        find_str = self.find_entry.get()
        if not find_str: return
        try:
            start_pos = self.target.index(tk.SEL_FIRST) if backwards else self.target.index(tk.SEL_LAST)
        except tk.TclError:
            start_pos = self.target.index(tk.INSERT)
        common_kwargs = {"nocase": not self.case_var.get(), "regexp": self.regex_var.get(), "count": self.match_len_var}
        pos = self.target.search(find_str, start_pos, stopindex="1.0" if backwards else tk.END, backwards=backwards, **common_kwargs)
        if not pos:
            wrap_pos = tk.END if backwards else "1.0"
            pos = self.target.search(find_str, wrap_pos, stopindex=start_pos, backwards=backwards, **common_kwargs)
            if pos: messagebox.showinfo("提示", "已回绕搜索。", parent=self)
        if pos:
            end_pos = f"{pos} + {self.match_len_var.get()}c"
            self._highlight_match(pos, end_pos)
            self.target.mark_set(tk.INSERT, end_pos if not backwards else pos)
        else:
            messagebox.showinfo("提示", "未找到指定内容", parent=self)

    def _highlight_match(self, start_pos, end_pos):
        self.target.tag_remove('found', '1.0', tk.END)
        self.target.tag_remove(tk.SEL, "1.0", tk.END)
        self.target.tag_add('found', start_pos, end_pos)
        self.target.tag_add(tk.SEL, start_pos, end_pos)
        self.target.see(start_pos)
        self.target.focus_set()

    def find_next(self): self._perform_find(backwards=False)
    def find_previous(self): self._perform_find(backwards=True)

    def replace(self):
        try:
            sel_start, sel_end = self.target.index(tk.SEL_FIRST), self.target.index(tk.SEL_LAST)
        except tk.TclError:
            self.find_next()
            return
        self.target.edit_separator()
        self.target.delete(sel_start, sel_end)
        self.target.insert(sel_start, self.replace_entry.get())
        self.target.edit_separator()
        self.find_next()

    def replace_all(self):
        find_text = self.find_entry.get()
        if not find_text: return
        self.app.replace_all(target_widget=self.target, find_text=find_text, replace_text=self.replace_entry.get(), use_regex=self.regex_var.get(), case_sensitive=self.case_var.get())

    def close_dialog(self):
        self.target.tag_remove('found', '1.0', tk.END)
        self.destroy()

class GoToLineDialog(tk.Toplevel):
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.app = app_instance
        self.transient(master)
        self.title("跳转到行")
        self.geometry("280x150")
        self.resizable(False, False)
        
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.grab_set()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)
        ttk.Label(input_frame, text="行号:").pack(side=tk.LEFT, padx=(0, 5))
        self.line_entry = ttk.Entry(input_frame)
        self.line_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.line_entry.focus_set()
        self.line_entry.bind("<Return>", self.on_ok)

        target_frame = ttk.Frame(main_frame)
        target_frame.pack(pady=5)
        self.target_var = tk.StringVar(value="input")
        ttk.Radiobutton(target_frame, text="输入框", variable=self.target_var, value="input").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(target_frame, text="输出框", variable=self.target_var, value="output").pack(side=tk.LEFT, padx=5)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="确定", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def on_ok(self, event=None):
        line_str = self.line_entry.get()
        target_choice = self.target_var.get()
        target_widget = self.app.input_text if target_choice == "input" else self.app.output_text

        try:
            line_num = int(line_str)
        except ValueError:
            messagebox.showerror("错误", "请输入一个有效的数字。", parent=self)
            return

        total_lines_str = target_widget.index('end-1c').split('.')[0]
        total_lines = int(total_lines_str) if total_lines_str else 0
        if not (1 <= line_num <= total_lines):
            messagebox.showerror("错误", f"行号必须在 1 到 {total_lines} 之间。", parent=self)
            return

        # 所有 state 操作都必须明确指向内部的 .text 组件
        was_disabled = (target_widget.text.cget("state") == tk.DISABLED)
        
        if was_disabled:
            target_widget.text.config(state=tk.NORMAL)

        for widget in [self.app.input_text, self.app.output_text]:
            widget.tag_remove("goto_line", "1.0", tk.END)
        target_widget.tag_add("goto_line", f"{line_num}.0", f"{line_num}.end")

        target_widget.mark_set(tk.INSERT, f"{line_num}.0")
        target_widget.see(f"{line_num}.0")
        target_widget.focus_set()

        if was_disabled:
            # [最终修正] 延迟操作同样要指向 .text 组件
            target_widget.after(100, lambda: target_widget.text.config(state=tk.DISABLED))

        self.destroy()
        
# #####################################################################
# 6. 主应用程序类
# #####################################################################
class GPTDictConverter:
    def __init__(self, root: TkinterDnD.Tk):
        self.root = root
        self.root.title(f"GPT字典编辑转换器   {APP_VERSION}")
        self.root.geometry("1000x600")
        self.root.protocol("WM_DELETE_WINDOW", self.ask_quit) # [新增] 退出时检查
        
        self.current_file_path: Optional[str] = None
        self.last_directory: str = os.path.expanduser("~") # [新增] 记忆目录

        self.format_names = {k: v["name"] for k, v in FORMAT_DEFINITIONS.items()}
        
        self._create_menu()
        self._create_widgets()
        self._setup_editor_features()
        
    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # --- 顶部控制区 ---
        top_control_frame = ttk.Frame(main_frame)
        top_control_frame.grid(row=0, column=0, columnspan=2, pady=5, sticky="ew")
        
        format_frame = ttk.Frame(top_control_frame)
        format_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(format_frame, text="输入格式:").pack(anchor=tk.W)
        self.input_format = ttk.Combobox(format_frame, values=["自动检测"] + list(self.format_names.values()), state="readonly", width=25)
        self.input_format.set("自动检测")
        self.input_format.pack(pady=2)
        self.input_format.bind("<<ComboboxSelected>>", self._on_input_format_change)
        
        ttk.Label(format_frame, text="输出格式:").pack(anchor=tk.W, pady=2)
        self.output_format = ttk.Combobox(format_frame, values=list(self.format_names.values()), state="readonly", width=25)
        self.output_format.set(self.format_names["GPPGUI_TOML"])
        self.output_format.pack(pady=2)
        self.output_format.bind("<<ComboboxSelected>>", lambda e: self.auto_convert())

        button_frame = ttk.Frame(top_control_frame)
        button_frame.pack(side=tk.LEFT, padx=20, anchor='n')
        
        btn_grid = ttk.Frame(button_frame)
        btn_grid.pack()
        ttk.Button(btn_grid, text="打开文件", command=self.open_file).grid(row=0, column=0, padx=5, pady=2)
        ttk.Button(btn_grid, text="保存输入", command=self.save_input_file).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(btn_grid, text="保存输出", command=self.save_output_file).grid(row=0, column=2, padx=5, pady=2)
        ttk.Button(btn_grid, text="转换", command=self.convert).grid(row=1, column=0, padx=5, pady=2)
        ttk.Button(btn_grid, text="清空", command=self.clear).grid(row=1, column=1, padx=5, pady=2)
        
        # 自动转换选项
        self.auto_convert_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(button_frame, text="自动转换", variable=self.auto_convert_var).pack(pady=5)
        
        # --- 内容编辑区 ---
        content_frame = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        content_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")

        input_pane = ttk.Frame(content_frame)
        input_header = ttk.Frame(input_pane)
        input_header.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(input_header, text="输入内容 (可拖入文件):").pack(side=tk.LEFT, anchor=tk.W)
        ttk.Button(input_header, text="复制", command=self.copy_input).pack(side=tk.LEFT, padx=10)
        self.input_text = EditorWithLineNumbers(input_pane, borderwidth=1, relief="solid")
        self.input_text.pack(expand=True, fill=tk.BOTH)
        self.input_text.drop_target_register(DND_FILES)
        self.input_text.dnd_bind('<<Drop>>', self.on_drop)
        
        output_pane = ttk.Frame(content_frame)
        output_header = ttk.Frame(output_pane)
        output_header.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(output_header, text="输出内容:").pack(side=tk.LEFT, anchor=tk.W)
        ttk.Button(output_header, text="复制", command=self.copy_output).pack(side=tk.LEFT, padx=10)
        ttk.Button(output_header, text="传至输入栏", command=self.transfer_output_to_input).pack(side=tk.LEFT)
        self.output_text = EditorWithLineNumbers(output_pane, state=tk.DISABLED, borderwidth=1, relief="solid")
        self.output_text.pack(expand=True, fill=tk.BOTH)

        content_frame.add(input_pane, weight=1)
        content_frame.add(output_pane, weight=1)
        
        # --- 状态栏 ---
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 0))

    def _setup_editor_features(self):
        # 共享编辑器样式
        editor_style = {
            "font": ("Consolas", 10), "background": "#FFFFFF", "foreground": "#000000",
            "insertbackground": "black", "selectbackground": "#ADD6FF", "selectforeground": "black",
            "inactiveselectbackground": "#E5E5E5", "insertwidth": 2, "padx": 5, "pady": 5,
        }
        self.input_text.config(**editor_style)
        self.output_text.config(**editor_style)

        # 统一配置标签颜色
        tag_colors = {
            "key": "#0000FF", "string": "#A31515", "punc": "#000000", "number": "#098658",
            "comment": "#008000", "tsv_tab": {"background": "#E0E8F0"},
            "tsv_space_delimiter": {"background": "#E0E8F0"},
            "highlight_duplicate": {"background": "#B4D5FF"},
            "found": {"background": "#FFD700"},
            "goto_line": {"background": "#FFFACD"},
        }
        
        # 循环处理每个文本框独立的事件绑定
        widgets = [self.input_text, self.output_text]
        for widget in widgets:
            # 应用标签配置
            for tag, props in tag_colors.items():
                if isinstance(props, dict):
                    widget.tag_configure(tag, **props)
                else:
                    widget.tag_configure(tag, foreground=props)
            
            # 为每个文本框的内部Text组件绑定划词高亮事件
            widget.text.bind("<<Selection>>", self._on_selection_change)

        # 只对输入框绑定修改和注释相关的事件
        self.input_text.text.bind("<KeyRelease>", self._on_text_change)
        self.input_text.text.bind("<Control-slash>", self._toggle_comment)
            
        # 将全局快捷键绑定到顶层窗口，确保任何时候都能触发
        self.root.bind_all("<Control-f>", self._show_find_replace_dialog)
        self.root.bind_all("<Control-g>", self._show_goto_line_dialog)
            
        self.highlight_job = None
        
    def _create_menu(self):
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="查找与替换 (Ctrl+F)", command=self._show_find_replace_dialog)
        edit_menu.add_command(label="跳转到行... (Ctrl+G)", command=self._show_goto_line_dialog)
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用教程", command=self._show_help_dialog)
        about_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="关于", menu=about_menu)
        about_menu.add_command(label="关于本软件", command=self._show_about_dialog)

    def ask_quit(self):
        if self.input_text.is_modified_flag:
            if messagebox.askyesno("退出确认", "输入内容已被修改但未保存，确定要退出吗？"):
                self.root.destroy()
        else:
            self.root.destroy()

    def auto_convert(self, event=None):
        if self.auto_convert_var.get():
            self.convert()

    # -------------------------------------------------------------
    # 核心事件处理
    # -------------------------------------------------------------
    def _on_text_change(self, event=None):
        widget = self.input_text
        widget.tag_remove("goto_line", "1.0", tk.END)
        if self.highlight_job:
            self.root.after_cancel(self.highlight_job)
        self.highlight_job = self.root.after(HIGHLIGHT_DELAY_MS, lambda: self._update_all_highlights(widget))
        self.auto_convert()
        
    def _on_selection_change(self, event=None):
        # 动态获取触发事件的控件
        if not event: return

        # event.widget 是内部的 tk.Text 组件，我们需要找到它的 EditorWithLineNumbers 父容器
        source_widget = event.widget
        parent_editor = source_widget
        while parent_editor and not isinstance(parent_editor, EditorWithLineNumbers):
            parent_editor = parent_editor.master
        
        # 如果找到了父容器，就对它执行高亮操作
        if parent_editor:
            self._highlight_duplicates_on_selection(parent_editor)
        
    def _on_input_format_change(self, event=None):
        if self.current_file_path:
            self.current_file_path = None
            self.status_var.set("输入格式已更改，文件关联已重置。")
        self.auto_convert()
        self._update_all_highlights(self.input_text)

    # -------------------------------------------------------------
    # 语法高亮
    # -------------------------------------------------------------
    def _update_all_highlights(self, widget: EditorWithLineNumbers):
        self._apply_syntax_highlighting(widget)
        self._highlight_duplicates_on_selection(widget)

    def _get_active_format_key(self, widget: EditorWithLineNumbers) -> Optional[str]:
        content = widget.get_content()
        if widget == self.input_text:
            format_name = self.input_format.get()
            if format_name == "自动检测":
                detected = self.detect_format(content)
                return self.get_format_key(detected, display_name=True) if detected else None
            return self.get_format_key(format_name, display_name=True)
        else: # output_text
            return self.get_format_key(self.output_format.get(), display_name=True)
    
    def _apply_syntax_highlighting(self, widget: EditorWithLineNumbers):
        all_tags = ["key", "string", "punc", "number", "comment", "tsv_tab", "tsv_space_delimiter"]
        for tag in all_tags:
            widget.tag_remove(tag, "1.0", tk.END)
        
        format_key = self._get_active_format_key(widget)
        if not format_key: return
        
        content = widget.get_content()
        
        # 将词法规则分离，避免命名冲突
        token_specs = {
            # 基础规则，适用于 TOML 和 JSON
            'BASE': [
                ('COMMENT', r'#.*$'),
                ('STRING', r'"([^"\\]*(?:\\.[^"\\]*)*)"'),
                ('PUNC', r'[\[\]{},=:]'),
            ],
            # 专用于 TOML 的关键字规则
            'GPPGUI_TOML': [('KEY', r'\b(org|rep|note)\b(?=\s*=)')],
            'GPPCLI_TOML': [('KEY', r'\b(note|replaceStr|searchStr)\b(?=\s*=)')],
            # 专用于 JSON 的关键字规则
            'AiNiee_JSON': [('KEY', r'"(src|dst|info)"(?=\s*:)')],
            # TSV 格式的完整独立规则
            'GalTransl_TSV': [
                ('COMMENT', r'//.*$'),
                ('TSV_TAB', r'\t'),
                ('TSV_SPACE_DELIMITER', r'(?<=\S) {4}(?=\S)'),
                # TSV中也可能有字符串，但我们通常不特殊高亮它们，除非有需求
            ]
        }
        
        # 根据格式选择正确的规则集
        if format_key == 'GalTransl_TSV':
            # TSV 使用它自己独立的规则集
            current_specs = token_specs['GalTransl_TSV']
        else:
            # 其他格式使用基础规则集，并附加上它们特有的规则
            current_specs = token_specs['BASE'] + token_specs.get(format_key, [])

        # 组合正则表达式
        # try-except 用于捕获任何潜在的正则表达式编译错误
        try:
            tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in current_specs)
        except re.error as e:
            print(f"正则表达式编译错误: {e}")
            # 可以在状态栏提示用户，或者弹窗
            self.status_var.set(f"语法高亮错误: {e}")
            return
        
        for mo in re.finditer(tok_regex, content, re.MULTILINE):
            kind = mo.lastgroup
            start, end = f"1.0 + {mo.start()} chars", f"1.0 + {mo.end()} chars"
            
            tag_map = {
                'KEY': 'key', 'STRING': 'string', 'PUNC': 'punc', 'NUMBER': 'number',
                'COMMENT': 'comment', 'TSV_TAB': 'tsv_tab', 'TSV_SPACE_DELIMITER': 'tsv_space_delimiter'
            }
            if kind in tag_map:
                # JSON的key包含引号，特殊处理以仅高亮引号内的文本
                if format_key == "AiNiee_JSON" and kind == 'KEY':
                    # mo.group(1) 对应 r'"(src|dst|info)"' 中的第一个括号
                    key_start_offset = mo.start(1)
                    key_end_offset = mo.end(1)
                    if key_start_offset != -1: # 确保捕获组匹配成功
                        key_start = f"1.0 + {key_start_offset} chars"
                        key_end = f"1.0 + {key_end_offset} chars"
                        widget.tag_add('key', key_start, key_end)
                else:
                    widget.tag_add(tag_map[kind], start, end)

    def _highlight_duplicates_on_selection(self, widget: EditorWithLineNumbers):
        widget.tag_remove("highlight_duplicate", "1.0", tk.END)
        try:
            selected_text = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected_text and len(selected_text.strip()) > 1:
                start_pos = "1.0"
                while True:
                    start_pos = widget.search(selected_text, start_pos, stopindex=tk.END, exact=True)
                    if not start_pos: break
                    if start_pos == widget.index(tk.SEL_FIRST): # 不高亮选中区本身
                        start_pos = widget.index(tk.SEL_LAST)
                        continue
                    end_pos = f"{start_pos} + {len(selected_text)}c"
                    widget.tag_add("highlight_duplicate", start_pos, end_pos)
                    start_pos = end_pos
        except tk.TclError:
            pass

    # -------------------------------------------------------------
    # 核心功能方法
    # -------------------------------------------------------------
    def convert(self):
        try:
            input_content = self.input_text.get_content()
            if not input_content.strip():
                self.output_text.clear()
                self.status_var.set("输入为空，已清空输出。")
                return

            input_format, output_format = self.input_format.get(), self.output_format.get()
            
            if input_format == "自动检测":
                detected_format_display = self.detect_format(input_content)
                if not detected_format_display:
                    raise ValueError("无法自动检测输入内容的格式。")
                self.input_format.set(detected_format_display)
                input_format = detected_format_display

            format_key = self.get_format_key(input_format, display_name=True)
            if input_format == output_format and format_key in ["GalTransl_TSV", "GPPGUI_TOML", "GPPCLI_TOML"]:
                output_content = self._reformat_current_format(input_content, input_format)
                status_msg = f"格式化完成: {input_format}"
            else:
                data = self.parse_input(input_content, input_format)
                output_key = self.get_format_key(output_format, display_name=True)
                output_content = self.format_output(data, output_key)
                status_msg = f"转换完成: {input_format} → {output_format}"

            self.output_text.set_content(output_content, reset_modified_flag=True)
            self._update_all_highlights(self.output_text)
            self.status_var.set(status_msg)

        except (ValueError, json.JSONDecodeError, toml.TomlDecodeError) as e:
            messagebox.showerror("错误", f"处理失败: {str(e)}")
            self.status_var.set(f"处理失败: {e}")
        except Exception as e:
            messagebox.showerror("未知错误", f"发生未知错误: {str(e)}")
            self.status_var.set("发生未知错误")
    
    def clear(self):
        self.input_text.clear()
        self.output_text.clear()
        self.current_file_path = None
        self.input_format.set("自动检测")
        self.status_var.set("已清空")

    def transfer_output_to_input(self):
        output_content = self.output_text.get_content()
        if not output_content:
            self.status_var.set("输出内容为空，无法传递。")
            return
        self.input_text.set_content(output_content)
        self.input_format.set(self.output_format.get())
        self.current_file_path = None
        self._update_all_highlights(self.input_text)
        self.status_var.set("已将输出传至输入，并同步格式。")

    def copy_input(self):
        content = self.input_text.get_content()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.status_var.set("输入内容已复制到剪贴板")
        else:
            self.status_var.set("输入内容为空")

    def copy_output(self):
        content = self.output_text.get_content()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.status_var.set("输出内容已复制到剪贴板")
        else:
            self.status_var.set("输出内容为空")
    
    # -------------------------------------------------------------
    # 文件操作
    # -------------------------------------------------------------
    def on_drop(self, event):
        file_path = event.data.strip('{}')
        self._open_file_path(file_path)

    def open_file(self):
        file_path = filedialog.askopenfilename(
            title="选择文件",
            initialdir=self.last_directory,
            filetypes=[("所有支持格式", "*.json;*.toml;*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            self.last_directory = os.path.dirname(file_path) # [改进] 记录目录
            self._open_file_path(file_path)

    def _open_file_path(self, file_path: str):
        if not file_path: return
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f: content = f.read()
            self.input_text.set_content(content, reset_modified_flag=True)
            self.current_file_path = file_path
            detected_format = self.detect_format(content)
            self.input_format.set(detected_format if detected_format else "自动检测")
            self.status_var.set(f"已打开: {os.path.basename(file_path)}")
            self._update_all_highlights(self.input_text)
            self.auto_convert()
        except Exception as e:
            messagebox.showerror("错误", f"打开文件失败: {str(e)}")
            self.status_var.set(f"打开失败: {e}")

    def save_input_file(self):
        # 简化保存逻辑
        content = self.input_text.get_content()
        if not content:
            messagebox.showwarning("警告", "输入内容为空，无法保存")
            return

        save_path = self.current_file_path
        if not save_path:
            input_format_name = self.input_format.get()
            if input_format_name == "自动检测":
                detected = self.detect_format(content)
                if detected: input_format_name = detected
            
            format_key = self.get_format_key(input_format_name, display_name=True)
            default_ext = FORMAT_DEFINITIONS.get(format_key, {}).get("ext", ".txt")
            
            save_path = filedialog.asksaveasfilename(
                title="保存输入内容",
                initialdir=self.last_directory,
                defaultextension=default_ext,
                filetypes=[(f"{input_format_name}", f"*{default_ext}"), ("所有文件", "*.*")]
            )
        
        if not save_path:
            self.status_var.set("保存已取消")
            return
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f: f.write(content)
            self.last_directory = os.path.dirname(save_path)
            self.current_file_path = save_path
            self.input_text.edit_reset()
            self.input_text.is_modified_flag = False
            self.status_var.set(f"文件已保存: {os.path.basename(save_path)}")
        except Exception as e:
            messagebox.showerror("错误", f"保存文件失败: {str(e)}")
            self.status_var.set("保存失败")

    def save_output_file(self):
        output_content = self.output_text.get_content()
        if not output_content:
            messagebox.showwarning("警告", "没有内容可保存")
            return
            
        output_format_display = self.output_format.get()
        format_key = self.get_format_key(output_format_display, display_name=True)
        default_ext = FORMAT_DEFINITIONS.get(format_key, {}).get("ext", ".txt")
        
        file_path = filedialog.asksaveasfilename(
            title="保存输出内容",
            initialdir=self.last_directory,
            defaultextension=default_ext,
            filetypes=[(f"{output_format_display}", f"*{default_ext}"), ("所有文件", "*.*")]
        )
        if not file_path:
            self.status_var.set("保存已取消")
            return
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f: f.write(output_content)
            self.last_directory = os.path.dirname(file_path)
            self.status_var.set(f"已保存输出: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("错误", f"保存输出内容失败: {str(e)}")

    # -------------------------------------------------------------
    # 辅助与工具方法
    # -------------------------------------------------------------
    def _toggle_comment(self, event):
        widget = event.widget
        format_key = self._get_active_format_key(self.input_text)
        comment_char = {"GPPGUI_TOML": "#", "GPPCLI_TOML": "#", "GalTransl_TSV": "//"}.get(format_key)
        if not comment_char: return "break"
        
        # 采用更可靠的方式来确定选中的行范围
        try:
            sel_start_index = widget.index(tk.SEL_FIRST)
            sel_end_index = widget.index(tk.SEL_LAST)
            
            start_line = int(sel_start_index.split('.')[0])
            end_line = int(sel_end_index.split('.')[0])
            
            # 如果选区的结尾在第0列，说明用户选中了之前行的完整内容（包括换行符），
            # 这种情况下不应处理结尾索引所在的新行。
            end_col = int(sel_end_index.split('.')[1])
            if end_col == 0:
                end_line -= 1
        except tk.TclError:
            # 如果没有选区，则只处理光标当前所在的行
            start_line = end_line = int(widget.index(tk.INSERT).split('.')[0])
        
        # 确保行号有效
        if end_line < start_line:
            return "break"

        widget.edit_separator()
        lines = [widget.get(f"{i}.0", f"{i}.end") for i in range(start_line, end_line + 1)]
        non_empty_lines = [line for line in lines if line.strip()]
        if not non_empty_lines:
            widget.edit_separator()
            return "break"
        
        all_commented = all(line.strip().startswith(comment_char) for line in non_empty_lines)

        for i in range(start_line, end_line + 1):
            line_content = widget.get(f"{i}.0", f"{i}.end")
            if all_commented:
                # 取消注释
                if line_content.strip():
                    idx = line_content.find(comment_char)
                    if idx != -1:
                        # 检查注释符后面是否跟了一个空格，有则一起删除
                        if line_content[idx+len(comment_char):].startswith(' '):
                            widget.delete(f"{i}.{idx}", f"{i}.{idx + len(comment_char) + 1}")
                        else:
                            widget.delete(f"{i}.{idx}", f"{i}.{idx + len(comment_char)}")
            elif line_content.strip():
                # 添加注释
                widget.insert(f"{i}.0", f"{comment_char} ")
        widget.edit_separator()
        self._update_all_highlights(self.input_text)
        return "break"
    
    def replace_all(self, target_widget: EditorWithLineNumbers, find_text: str, replace_text: str, use_regex: bool, case_sensitive: bool):
        content = target_widget.get_content()
        total_count = 0
        try:
            if use_regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                new_content, total_count = re.subn(find_text, replace_text, content, flags=flags)
            else:
                if not case_sensitive:
                    # 高效的不区分大小写替换
                    flags = re.IGNORECASE
                    new_content, total_count = re.subn(re.escape(find_text), replace_text, content, flags=flags)
                else:
                    total_count = content.count(find_text)
                    new_content = content.replace(find_text, replace_text)
        except re.error as e:
            messagebox.showerror("正则表达式错误", str(e))
            return

        if total_count > 0:
            target_widget.set_content(new_content)
            self._update_all_highlights(target_widget)
            self.status_var.set(f"已完成 {total_count} 处替换。")
            messagebox.showinfo("成功", f"已完成 {total_count} 处替换。")
        else:
            messagebox.showinfo("提示", "未找到可替换的内容。")

    def get_format_key(self, name: str, display_name: bool = False) -> Optional[str]:
        if display_name:
            for key, value in self.format_names.items():
                if value == name: return key
        return name if name in self.format_names else None
        
    def detect_format(self, content: str) -> Optional[str]:
        content = content.strip()
        if not content: return None
        if any(line.strip().startswith('//') or '\t' in line or re.search(r'\S {4}\S', line) for line in content.split('\n') if not line.strip().startswith("#")):
            return self.format_names["GalTransl_TSV"]
        if 'gptDict' in content or '[[gptDict]]' in content:
            try:
                toml.loads(content)
                if '[[gptDict]]' in content: return self.format_names["GPPCLI_TOML"]
                return self.format_names["GPPGUI_TOML"]
            except toml.TomlDecodeError: pass
        if content.startswith('[') and content.endswith(']'):
            try:
                data = json.loads(content)
                if isinstance(data, list) and data and all(k in data[0] for k in ['src', 'dst', 'info']):
                    return self.format_names["AiNiee_JSON"]
            except json.JSONDecodeError: pass
        return None
        
    def parse_input(self, content: str, format_display_name: str) -> List[Dict[str, str]]:
        format_key = self.get_format_key(format_display_name, display_name=True)
        data: List[Dict[str, str]] = []
        if content.startswith('\ufeff'): content = content[1:]
        if not content.strip(): return []
        
        def parse_tsv_line(line: str) -> Optional[Dict[str, str]]:
            line = line.strip()
            if not line or line.startswith(('//', '#')): return None
            parts = re.split(r'\t|(?<=\S) {4}(?=\S)', line, maxsplit=2)
            if len(parts) >= 2:
                return {'org': parts[0].strip(), 'rep': parts[1].strip(), 'note': parts[2].strip() if len(parts) > 2 else ''}
            return None

        if format_key == "AiNiee_JSON":
            json_data = json.loads(content)
            for item in json_data: data.append({'org': item.get('src', ''), 'rep': item.get('dst', ''), 'note': item.get('info', '')})
        elif format_key == "GPPGUI_TOML":
            toml_data = toml.loads(content)
            for item in toml_data.get('gptDict', []): data.append({'org': item.get('org', ''), 'rep': item.get('rep', ''), 'note': item.get('note', '')})
        elif format_key == "GPPCLI_TOML":
            toml_data = toml.loads(content)
            for item in toml_data.get('gptDict', []): data.append({'org': item.get('searchStr', ''), 'rep': item.get('replaceStr', ''), 'note': item.get('note', '')})
        elif format_key == "GalTransl_TSV":
            for line in content.split('\n'):
                if parsed := parse_tsv_line(line): data.append(parsed)
        return data

    def format_output(self, data: List[Dict[str, str]], format_key: str) -> str:
        escape = lambda text: text.replace("'", "''")
        if format_key == "AiNiee_JSON":
            json_data = [{'src': item['org'], 'dst': item['rep'], 'info': item['note']} for item in data]
            return json.dumps(json_data, ensure_ascii=False, indent=2)
        elif format_key == "GPPGUI_TOML":
            lines = ["gptDict = ["]
            for item in data:
                lines.append(f"\t{{ org = '{escape(item['org'])}', rep = '{escape(item['rep'])}', note = '{escape(item['note'])}' }},")
            lines.append("]")
            return "\n".join(lines)
        elif format_key == "GPPCLI_TOML":
            return "\n\n".join([f"[[gptDict]]\nnote = '{escape(item['note'])}'\nreplaceStr = '{escape(item['rep'])}'\nsearchStr = '{escape(item['org'])}'" for item in data])
        elif format_key == "GalTransl_TSV":
            return "\n".join([f"{item['org']}\t{item['rep']}" + (f"\t{item['note']}" if item['note'] else "") for item in data])
        return ""
        
    def _reformat_current_format(self, content: str, format_display_name: str) -> str:
        # 相同格式转换时，重新格式化并保留注释
        data = self.parse_input(content, format_display_name)
        output_key = self.get_format_key(format_display_name, display_name=True)
        return self.format_output(data, output_key)

    # -------------------------------------------------------------
    # 对话框显示
    # -------------------------------------------------------------
    def _show_find_replace_dialog(self, event=None):
        FindReplaceDialog(self.root, self.input_text, app_instance=self)
        return "break"
    
    def _show_goto_line_dialog(self, event=None):
        GoToLineDialog(self.root, app_instance=self)
        return "break"

    def _show_about_dialog(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("关于")
        about_win.transient(self.root)
        about_win.geometry("420x240")
        about_win.resizable(False, False)

        main_frame = ttk.Frame(about_win, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(main_frame, text="GPT字典编辑转换器", font=("", 12, "bold")).pack(pady=(0, 10))
        ttk.Label(main_frame, text=f"版本: {APP_VERSION}").pack(pady=2)
        
        link_font = tkFont.Font(family="Helvetica", size=10, underline=True)
        
        author_frame = ttk.Frame(main_frame)
        author_frame.pack(pady=2)
        ttk.Label(author_frame, text="作者: ").pack(side=tk.LEFT)
        author_link = ttk.Label(author_frame, text="natsumerinchan", foreground="blue", cursor="hand2", font=link_font)
        author_link.pack(side=tk.LEFT)
        author_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/natsumerinchan"))

        license_frame = ttk.Frame(main_frame)
        license_frame.pack(pady=2)
        ttk.Label(license_frame, text="开源许可证: ").pack(side=tk.LEFT)
        license_link = ttk.Label(license_frame, text="MIT License", foreground="blue", cursor="hand2", font=link_font)
        license_link.pack(side=tk.LEFT)
        license_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/natsumerinchan/GPTDictEditor/blob/master/LICENSE"))

        repo_link = ttk.Label(main_frame, text="https://github.com/natsumerinchan/GPTDictEditor", foreground="blue", cursor="hand2", font=link_font)
        repo_link.pack(pady=10)
        repo_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/natsumerinchan/GPTDictEditor"))
        
        ok_button = ttk.Button(main_frame, text="确定", command=about_win.destroy)
        ok_button.pack(pady=15)
        
        about_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - about_win.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - about_win.winfo_height()) // 2
        about_win.geometry(f"+{x}+{y}")
        
        about_win.focus_set()
        about_win.grab_set()
    
    def _show_help_dialog(self):
        help_win = tk.Toplevel(self.root)
        help_win.title("使用教程")
        help_win.transient(self.root)
        help_win.geometry("700x600")
        
        # Markdown格式的帮助信息
        help_text_md = """
# GPT字典编辑转换器使用教程

本工具旨在为不同格式的字典/词典文件提供一个统一的编辑和转换平台。

## 一、核心工作流程

### 1、 **加载数据** (三选一)

- **打开文件**: 点击 `打开文件` 按钮，选择一个支持的 `.json`, `.toml`, 或 `.txt` 文件。
- **粘贴文本**: 直接将文本内容粘贴到左侧的 **“输入内容”** 框中。
- **拖放文件**: 将文件直接从您的文件管理器拖拽到 **“输入内容”** 框中。

### 2、  **选择格式**

- **输入格式**: 程序会 **`自动检测`** 加载内容的格式。如果检测失败或不准确，  
您必须从下拉菜单中 **手动指定** 正确的格式。
- **输出格式**: 从右侧的下拉菜单中选择您想要转换的目标格式。

### 3、  **执行转换**

- **自动转换** (默认开启): 每当输入内容或格式选择发生变化时，程序会自动进行转换。
- **手动转换**: 取消勾选 `自动转换` 后，需点击 `转换` 按钮来触发。

### 4、  **保存结果**

- 点击 `保存输出`，将右侧 **“输出内容”** 框中的结果保存为新文件。
- 点击 `保存输入`，可将左侧 **“输入内容”** 框中的文本保存。若已打开文件，则可覆盖保存。

## 二、界面与功能详解

- **`清空`**: 一键清除输入和输出框的所有内容，并重置文件关联。
- **`复制`**: 快速将对应文本框的全部内容复制到系统剪贴板。
- **`传至输入栏`**: 将 **“输出内容”** 框中的结果发送到 **“输入内容”** 框，并自动同步格式。  
此功能对于“链式转换”（如 A->B->C）或对转换结果进行二次编辑非常有用。

## 三、高级编辑功能

*这些功能主要在左侧的 **“输入内容”** 框中生效。*

### **查找与替换 (`Ctrl+F`)**  

- 在输入框内进行文本搜索和替换。
- 支持 **“区分大小写”** 和强大的 **“正则表达式”** 模式。

### **注释/取消注释 (`Ctrl+/`)**

- 自动为当前行或选中的多行添加/移除对应格式的注释符。
- TOML 使用 `#`，TSV 使用 `//`。(此功能对JSON格式无效)

### **跳转到行 (`Ctrl+G`)**

- 快速跳转到输入或输出框的指定行。

### **语法高亮**

- 程序会根据当前选择的格式自动对文本进行着色，提高可读性。
- TSV 格式特殊高亮：**制表符(Tab)** 和作为分隔符的 **四个连续空格** 会显示背景色，以便明确区分。

### **选中词高亮**

- 在输入框中选中一段文本时，所有与之相同的内容都会被自动高亮。

## 四、支持的格式说明

- **`AiNiee/LinguaGacha JSON`**: JSON 数组格式，每个对象包含 `src` (原文), `dst` (译文), `info` (备注) 键。
- **`GalTranslPP GUI TOML`**: TOML 格式，包含一个名为 `gptDict` 的表数组，每个表包含 `org`, `rep`, `note` 键。
- **`GalTranslPP CLI TOML`**: TOML 格式，每个条目由独立的 `[[gptDict]]` 表定义，包含 `searchStr`, `replaceStr`, `note` 键。
- **`GalTransl TSV`**: 纯文本格式，使用制表符 (Tab) 或四个空格分隔。以 `//` 开头的行为注释。

        """

        main_frame = ttk.Frame(help_win, padding=10)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Markdown to HTML
        html_content = markdown.markdown(help_text_md, extensions=['fenced_code', 'tables'])

        # Use HTMLScrolledText from tkhtmlview to display the rendered HTML
        html_text = HTMLScrolledText(main_frame, background="white")
        html_text.pack(expand=True, fill=tk.BOTH)
        html_text.set_html(html_content)

        # Bottom button
        button_frame = ttk.Frame(help_win, padding=(0, 0, 0, 10))
        button_frame.pack(fill=tk.X)
        ok_button = ttk.Button(button_frame, text="关闭", command=help_win.destroy)
        ok_button.pack()

        help_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - help_win.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - help_win.winfo_height()) // 2
        help_win.geometry(f"+{x}+{y}")
        
        help_win.focus_set()
        help_win.grab_set()


# #####################################################################
# 7. 主函数
# #####################################################################
def main():
    root = TkinterDnD.Tk()
    app = GPTDictConverter(root)
    root.mainloop()

if __name__ == "__main__":
    main()