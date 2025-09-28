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
    # 如果 toml 缺失，但 tkinter 存在，则用弹窗提示
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    messagebox.showerror(
        "缺少依赖",
        "错误：缺少 'toml' 包。\n\n请在命令行运行以下命令进行安装：\npip install toml"
    )
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

# #####################################################################
# 新增: 带行号的自定义编辑器组件
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

        self.text.bind("<<Modified>>", self._on_change_proxy)
        self.text.bind("<Configure>", self._on_change_proxy)
        self.text.bind("<KeyRelease>", self._on_change_proxy)
        self.text.bind("<ButtonRelease-1>", self._on_change_proxy)

        self._redraw_job = None
        self.text.edit_modified(False)

    def on_text_scroll(self, first, last):
        self.vbar.set(first, last)
        self.linenumbers.yview_moveto(first)
        self._on_change_proxy()

    def yview(self, *args):
        self.text.yview(*args)
        self.linenumbers.yview(*args)
        self._on_change_proxy()
        return "break"

    def _on_change_proxy(self, event=None):
        if self._redraw_job:
            self.after_cancel(self._redraw_job)
        self._redraw_job = self.after(20, self.redraw_line_numbers)
        
        if self.text.edit_modified():
            self.text.edit_modified(False)

    def redraw_line_numbers(self):
        self.linenumbers.delete("all")

        try:
            total_lines_str = self.text.index('end-1c').split('.')[0]
            line_count = int(total_lines_str) if total_lines_str else 1
            new_width = 20 + len(total_lines_str) * 8
            if self.linenumbers.winfo_width() != new_width:
                self.linenumbers.config(width=new_width)

            current_line = self.text.index(tk.INSERT).split('.')[0]
            
            i = self.text.index("@0,0")
            while True:
                dline = self.text.dlineinfo(i)
                if dline is None: break
                
                y = dline[1]
                linenum = i.split('.')[0]
                
                color = "#1e1e1e" if linenum == current_line else "#858585"

                self.linenumbers.create_text(
                    new_width - 5, y, anchor=tk.NE, text=linenum,
                    fill=color, font=self.text_font
                )
                i = self.text.index(f"{i}+1line")
        except (tk.TclError, ValueError):
            pass

    def config(self, cnf=None, **kw):
        all_options = (cnf or {}).copy()
        all_options.update(kw)
        
        text_keys = tk.Text().keys()
        text_kw = {k: v for k, v in all_options.items() if k in text_keys}
        frame_kw = {k: v for k, v in all_options.items() if k not in text_keys}
            
        if 'font' in text_kw:
            self.text_font = text_kw['font']
        
        super().config(**frame_kw)
        if text_kw:
            self.text.config(**text_kw)

    def __getattr__(self, name):
        try:
            return getattr(self.text, name)
        except AttributeError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


# #####################################################################
# 查找与替换对话框类
# #####################################################################
class FindReplaceDialog(tk.Toplevel):
    def __init__(self, master, target_widget, app_instance):
        super().__init__(master)
        self.transient(master)
        self.title("查找与替换")
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

        common_kwargs = {
            "nocase": not self.case_var.get(), 
            "regexp": self.regex_var.get(),
            "count": self.match_len_var
        }
        
        pos = self.target.search(find_str, start_pos, stopindex="1.0" if backwards else tk.END, backwards=backwards, **common_kwargs)
        if not pos:
            wrap_pos = tk.END if backwards else "1.0"
            stop_index = start_pos
            pos = self.target.search(find_str, wrap_pos, stopindex=stop_index, backwards=backwards, **common_kwargs)
            if pos: messagebox.showinfo("提示", "已回绕搜索。", parent=self)

        if pos:
            match_length = self.match_len_var.get()
            end_pos = f"{pos} + {match_length}c"
            
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

    def _find_driver(self, direction):
        self._perform_find(backwards=(direction == -1))

    def find_next(self): self._find_driver(1)
    def find_previous(self): self._find_driver(-1)

    def replace(self):
        try:
            sel_start = self.target.index(tk.SEL_FIRST)
            sel_end = self.target.index(tk.SEL_LAST)
        except tk.TclError:
            self.find_next()
            return

        replace_text = self.replace_entry.get()
        self.target.edit_separator()
        self.target.delete(sel_start, sel_end)
        self.target.insert(sel_start, replace_text)
        self.target.edit_separator()
        self.find_next()

    def replace_all(self):
        find_text = self.find_entry.get()
        if not find_text: return
        
        self.app.replace_all(
            target_widget=self.target, find_text=find_text, replace_text=self.replace_entry.get(),
            use_regex=self.regex_var.get(), case_sensitive=self.case_var.get())

    def close_dialog(self):
        self.target.tag_remove('found', '1.0', tk.END)
        self.destroy()

# #####################################################################
# 新增: 转到行对话框
# #####################################################################
class GoToLineDialog(tk.Toplevel):
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.app = app_instance
        self.transient(master)
        self.title("转到行")
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

        total_lines = int(target_widget.index('end-1c').split('.')[0])
        if not (1 <= line_num <= total_lines):
            messagebox.showerror("错误", f"行号必须在 1 到 {total_lines} 之间。", parent=self)
            return

        was_disabled = (target_widget.text.cget("state") == tk.DISABLED)
        
        if was_disabled:
            target_widget.config(state=tk.NORMAL)

        for widget in [self.app.input_text, self.app.output_text]:
            widget.tag_remove("goto_line", "1.0", tk.END)
        target_widget.tag_add("goto_line", f"{line_num}.0", f"{line_num}.end")

        target_widget.mark_set(tk.INSERT, f"{line_num}.0")
        target_widget.see(f"{line_num}.0")
        target_widget.focus_set()

        if was_disabled:
            target_widget.config(state=tk.DISABLED)

        self.destroy()

# #####################################################################
# 主应用程序类
# #####################################################################
class GPTDictConverter:
    def __init__(self, root):
        self.root = root
        self.version = "v1.0.3"
        self.root.title(f"GPT字典编辑转换器   {self.version}")
        self.root.geometry("1000x600")
        self.current_file_path = None
        
        self.format_names = {
            "AiNiee_JSON": "AiNiee/LinguaGacha JSON格式",
            "GPPGUI_TOML": "GalTranslPP GUI TOML格式", 
            "GPPCLI_TOML": "GalTranslPP CLI TOML格式",
            "GalTransl_TSV": "GalTransl TSV格式"
        }
        
        self._create_menu()

        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        top_control_frame = ttk.Frame(main_frame)
        top_control_frame.grid(row=0, column=0, columnspan=3, pady=5, sticky=tk.N)
        
        format_frame = ttk.Frame(top_control_frame)
        format_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(format_frame, text="输入格式:").pack(anchor=tk.W, pady=2)
        self.input_format = ttk.Combobox(format_frame, values=["自动检测"] + list(self.format_names.values()), 
                                      state="readonly", width=25)
        self.input_format.set("自动检测")
        self.input_format.pack(pady=2)
        self.input_format.bind("<<ComboboxSelected>>", self._on_input_format_change)
        
        ttk.Label(format_frame, text="输出格式:").pack(anchor=tk.W, pady=2)
        self.output_format = ttk.Combobox(format_frame, values=list(self.format_names.values()), 
                                       state="readonly", width=25)
        self.output_format.set("GalTranslPP GUI TOML格式")
        self.output_format.pack(pady=2)
        
        button_frame = ttk.Frame(top_control_frame)
        button_frame.pack(side=tk.LEFT, padx=20)
        
        ttk.Button(button_frame, text="打开文件", command=self.open_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="保存输入内容", command=self.save_input_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="保存输出内容", command=self.save_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="转换", command=self.convert).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空", command=self.clear).pack(side=tk.LEFT, padx=5)
        
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(2, weight=1)
        content_frame.rowconfigure(0, weight=1)

        input_frame = ttk.Frame(content_frame)
        input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        ttk.Label(input_frame, text="输入内容:").pack(anchor=tk.W, pady=5)
        self.input_text = EditorWithLineNumbers(
            input_frame,
            selectbackground="black", selectforeground="white",
            borderwidth=1, relief="solid",
            highlightthickness=1, highlightbackground="#c0c0c0"
        )
        self.input_text.pack(expand=True, fill=tk.BOTH)

        transfer_frame = ttk.Frame(content_frame)
        transfer_frame.grid(row=0, column=1, sticky=tk.N)
        ttk.Button(transfer_frame, text="←", command=self.transfer_output_to_input, width=2).pack(pady=0, fill=tk.Y, expand=True)

        output_frame = ttk.Frame(content_frame)
        output_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        output_header_frame = ttk.Frame(output_frame)
        output_header_frame.pack(fill=tk.X)
        ttk.Label(output_header_frame, text="输出内容:").pack(side=tk.LEFT)
        ttk.Button(output_header_frame, text="复制", command=self.copy_output).pack(side=tk.LEFT, padx=10)
        
        self.output_text = EditorWithLineNumbers(
            output_frame, state=tk.DISABLED,
            selectbackground="black", selectforeground="white",
            borderwidth=1, relief="solid",
            highlightthickness=1, highlightbackground="#c0c0c0"
        )
        self.output_text.pack(expand=True, fill=tk.BOTH)
        
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        self._setup_editor_features()
        
    def _on_input_format_change(self, event=None):
        if self.current_file_path:
            self.current_file_path = None
            self.status_var.set("输入格式已更改，文件关联已重置。")
        
    def transfer_output_to_input(self):
        self.output_text.config(state=tk.NORMAL)
        output_content = self.output_text.get("1.0", tk.END).strip()
        self.output_text.config(state=tk.DISABLED)
        if not output_content:
            self.status_var.set("输出内容为空，无法传递。")
            return
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", output_content)
        current_output_format = self.output_format.get()
        self.input_format.set(current_output_format)
        self.current_file_path = None
        self._update_all_highlights(self.input_text)
        self.status_var.set("已将输出传至输入，并同步格式。")
        
    def copy_output(self):
        self.output_text.config(state=tk.NORMAL)
        content = self.output_text.get("1.0", tk.END).strip()
        self.output_text.config(state=tk.DISABLED)
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.status_var.set("输出内容已复制到剪贴板")
        else:
            self.status_var.set("输出内容为空")
            
    def _create_menu(self):
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="查找与替换 (Ctrl+F)", command=self._show_find_replace_dialog)
        edit_menu.add_command(label="转到行... (Ctrl+G)", command=self._show_goto_line_dialog)

        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用教程", command=self._show_help_dialog)

        about_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="关于", menu=about_menu)
        about_menu.add_command(label="关于本软件", command=self._show_about_dialog)

    def _show_about_dialog(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("关于")
        about_win.transient(self.root)
        about_win.geometry("420x240")
        about_win.resizable(False, False)

        main_frame = ttk.Frame(about_win, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(main_frame, text="GPT字典编辑转换器", font=("", 12, "bold")).pack(pady=(0, 10))
        ttk.Label(main_frame, text=f"版本: {self.version}").pack(pady=2)
        
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
        help_win.geometry("600x450")
        
        help_text_content = """
        欢迎使用 GPT字典编辑转换器！

        基本流程:
        1. 打开文件或粘贴内容:
           - 点击“打开文件”按钮选择一个 .json, .toml, 或 .txt 文件。
           - 或者直接将文本内容粘贴到“输入内容”框中。
        
        2. 格式识别:
           - 程序会自动尝试识别输入内容的格式，并在“输入格式”下拉框中显示。
           - 如果识别错误或失败，你可以手动指定正确的输入格式。

        3. 选择输出格式:
           - 在“输出格式”下拉框中选择你想要转换的目标格式。

        4. 执行转换:
           - 点击“转换”按钮，转换后的内容将显示在“输出内容”框中。
           - 如果输入和输出格式相同（如 TSV->TSV），程序会格式化文件
             并保留所有注释。

        5. 保存结果:
           - 点击“保存输出内容”按钮，将输出内容保存到新文件中。
           - 点击“保存输入内容”按钮，可以直接覆盖保存已打开的文件，
             或者将当前输入框的内容格式化后另存为新文件。

        -------------------------------------------------------------

        其他功能:
        - 清空: 点击“清空”按钮以清除输入和输出框的所有内容。
        - 复制: 点击输出框旁的“复制”按钮，快速复制输出结果。
        - ← 按钮: 点击输入框和输出框之间的 ← 按钮，可以将当前输出内容
          转移到输入框，方便进行二次编辑或格式转换。
        
        编辑功能 (在输入框中生效):
        - 查找与替换 (快捷键 Ctrl+F):
          - 打开查找与替换对话框。
          - 支持区分大小写、正则表达式等高级功能。

        - 注释/取消注释 (快捷键 Ctrl+/):
          - 快速为选中行或当前光标所在行添加或移除注释符号 (# 或 //)。
          - 支持多行操作。

        - 语法高亮:
          - 程序会自动为不同格式的文本（如JSON, TOML, TSV）进行语法高亮，
            方便阅读。（TSV会将制表符\\t显示为浅蓝色，4个连续空格显示为黑色）

        - 选中词高亮:
          - 当你选中一段文本时，输入框中所有相同的文本都会被高亮显示。
        """

        text_area = scrolledtext.ScrolledText(help_win, wrap=tk.WORD, font=("", 10), padx=5, pady=5)
        text_area.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        text_area.insert(tk.END, help_text_content)
        text_area.config(state=tk.DISABLED)

        help_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - help_win.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - help_win.winfo_height()) // 2
        help_win.geometry(f"+{x}+{y}")
        
        help_win.focus_set()
        help_win.grab_set()

    def _setup_editor_features(self):
        widgets = [self.input_text, self.output_text]
        for widget in widgets: # 'widget' is an EditorWithLineNumbers instance
            widget.config(
                font=("Consolas", 10),
                background="#FFFFFF",
                foreground="#000000",
                insertbackground="#000000",
                selectbackground="#ADD6FF",
                selectforeground="#000000",
                inactiveselectbackground="#E5E5E5",
                insertwidth=2,
                padx=5,
                pady=5,
            )
            
            # tag_configure can be called on the wrapper thanks to __getattr__
            widget.tag_configure("key", foreground="#0000FF")
            widget.tag_configure("string", foreground="#A31515")
            widget.tag_configure("punc", foreground="#000000")
            widget.tag_configure("number", foreground="#098658")
            widget.tag_configure("comment", foreground="#008000")
            widget.tag_configure("tsv_tab", background="#E5E5E5")
            widget.tag_configure("tsv_space_delimiter", background="#E5E5E5", foreground="black")
            widget.tag_configure("highlight_duplicate", background="#7FB4FF")
            widget.tag_configure('found', background='#ADD6FF')
            widget.tag_configure('goto_line', background='#fffacd')
            
            # ### 修正: 必须将事件绑定到拥有焦点的内部 Text 组件上 ###
            internal_text_widget = widget.text
            
            # 这些事件由内部 Text 组件触发
            internal_text_widget.bind("<KeyRelease>", self._on_text_change)
            internal_text_widget.bind("<ButtonRelease-1>", self._on_text_change)
            
            # 快捷键事件也必须绑定在内部 Text 组件上
            internal_text_widget.bind("<Control-slash>", self._toggle_comment)
            internal_text_widget.bind("<Control-f>", self._show_find_replace_dialog)
            internal_text_widget.bind("<Control-g>", self._show_goto_line_dialog)
            
        self.highlight_job = None
        
    def _on_text_change(self, event=None):
        if hasattr(self, 'highlight_job') and self.highlight_job:
            self.root.after_cancel(self.highlight_job)
        
        widget = event.widget if event else self.root.focus_get()

        if isinstance(widget, tk.Text):
            widget.tag_remove("goto_line", "1.0", tk.END)

            parent_editor = widget
            while not isinstance(parent_editor, EditorWithLineNumbers) and parent_editor is not None:
                parent_editor = parent_editor.master
            
            if parent_editor:
                self.highlight_job = self.root.after(200, lambda: self._update_all_highlights(parent_editor))
            
    def _update_all_highlights(self, widget):
        self._apply_syntax_highlighting(widget)
        self._highlight_duplicates_on_selection(widget)
        
    def _show_find_replace_dialog(self, event=None):
        target = self.input_text
        FindReplaceDialog(self.root, target, app_instance=self)
        return "break"
    
    def _show_goto_line_dialog(self, event=None):
        GoToLineDialog(self.root, app_instance=self)
        return "break"

    def replace_all(self, target_widget, find_text, replace_text, use_regex, case_sensitive):
        content = target_widget.get("1.0", "end-1c")
        lines = content.split('\n')
        new_lines = []
        total_count = 0
        flags = re.IGNORECASE if not case_sensitive else 0
        
        try:
            if use_regex:
                pattern = re.compile(find_text, flags)
                for line in lines:
                    new_line, count = pattern.subn(replace_text, line)
                    new_lines.append(new_line)
                    total_count += count
            else:
                if case_sensitive:
                    for line in lines:
                        count = line.count(find_text)
                        if count > 0:
                            new_lines.append(line.replace(find_text, replace_text))
                            total_count += count
                        else:
                            new_lines.append(line)
                else:
                    pattern = re.compile(re.escape(find_text), flags)
                    for line in lines:
                        new_line, count = pattern.subn(replace_text, line)
                        new_lines.append(new_line)
                        total_count += count
        except re.error as e:
            messagebox.showerror("正则表达式错误", str(e))
            return

        if total_count > 0:
            new_content = "\n".join(new_lines)
            target_widget.edit_separator()
            target_widget.delete("1.0", tk.END)
            target_widget.insert("1.0", new_content)
            target_widget.edit_separator()
            self._update_all_highlights(target_widget)
            messagebox.showinfo("成功", f"已完成 {total_count} 处替换。")
        else:
            messagebox.showinfo("提示", "未找到可替换的内容。")

    def _toggle_comment(self, event):
        widget = event.widget
        format_name = self.input_format.get()
        if format_name == "自动检测":
            content = widget.get("1.0", tk.END)
            detected = self.detect_format(content)
            format_key = self.get_format_key(detected, display_name=True) if detected else None
        else:
            format_key = self.get_format_key(format_name, display_name=True)
        comment_char = {"GPPGUI_TOML": "#", "GPPCLI_TOML": "#", "GalTransl_TSV": "//"}.get(format_key)
        if not comment_char: return "break"
        
        try:
            sel_start, sel_end = widget.index(tk.SEL_FIRST), widget.index(tk.SEL_LAST)
            start_line, end_line = int(sel_start.split('.')[0]), int(sel_end.split('.')[0])
        except tk.TclError:
            line_num_str = widget.index(tk.INSERT).split('.')[0]
            start_line = end_line = int(line_num_str)
        
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
                if line_content.strip():
                    if f"{comment_char} " in line_content:
                        idx = line_content.find(f"{comment_char} ")
                        widget.delete(f"{i}.{idx}", f"{i}.{idx + len(comment_char) + 1}")
                    elif comment_char in line_content:
                        idx = line_content.find(comment_char)
                        widget.delete(f"{i}.{idx}", f"{i}.{idx + len(comment_char)}")
            elif line_content.strip():
                widget.insert(f"{i}.0", f"{comment_char} ")
        widget.edit_separator()
        
        parent_editor = widget
        while not isinstance(parent_editor, EditorWithLineNumbers):
            parent_editor = parent_editor.master
        self._update_all_highlights(parent_editor)
        return "break"
        
    def _apply_syntax_highlighting(self, widget):
        tags = ["key", "string", "punc", "number", "comment", "tsv_tab", "tsv_space_delimiter"]
        for tag in tags:
            widget.tag_remove(tag, "1.0", tk.END)
            
        format_key = None
        content = widget.get("1.0", tk.END)
        
        if widget == self.input_text:
            format_name = self.input_format.get()
            if format_name == "自动检测":
                detected = self.detect_format(content)
                format_key = self.get_format_key(detected, display_name=True) if detected else None
            else:
                format_key = self.get_format_key(format_name, display_name=True)
        else:
            format_name = self.output_format.get()
            format_key = self.get_format_key(format_name, display_name=True)
            
        if format_key == "GalTransl_TSV":
            for match in re.finditer(r"\t", content):
                start, end = f"1.0 + {match.start()} chars", f"1.0 + {match.end()} chars"
                widget.tag_add("tsv_tab", start, end)
            for match in re.finditer(r'(?<=\S) {4}(?=\S)', content):
                start, end = f"1.0 + {match.start()} chars", f"1.0 + {match.end()} chars"
                widget.tag_add("tsv_space_delimiter", start, end)
            for match in re.finditer(r"//.*$", content, re.MULTILINE):
                widget.tag_add("comment", f"1.0 + {match.start()} chars", f"1.0 + {match.end()} chars")
        else:
            for match in re.finditer(r"#.*$", content, re.MULTILINE):
                widget.tag_add("comment", f"1.0 + {match.start()} chars", f"1.0 + {match.end()} chars")
            for match in re.finditer(r'"([^"\\]*(?:\\.[^"\\]*)*)"\s*:', content):
                widget.tag_add("key", f"1.0 + {match.start(1)} chars", f"1.0 + {match.end(1)} chars")
            for match in re.finditer(r"^\s*(\w+)\s*=", content, re.MULTILINE):
                widget.tag_add("key", f"1.0 + {match.start(1)} chars", f"1.0 + {match.end(1)} chars")
            for match in re.finditer(r"('[^']*'|\"[^\"\\]*(?:\\.[^\"\\]*)*\")", content):
                if "key" not in widget.tag_names(f"1.0 + {match.start()} chars"):
                    widget.tag_add("string", f"1.0 + {match.start()} chars", f"1.0 + {match.end()} chars")
            for match in re.finditer(r"[\[\]{},=:]", content):
                if not "comment" in widget.tag_names(f"1.0 + {match.start()} chars"):
                    widget.tag_add("punc", f"1.0 + {match.start()} chars", f"1.0 + {match.end()} chars")
                    
    def _highlight_duplicates_on_selection(self, widget):
        widget.tag_remove("highlight_duplicate", "1.0", tk.END)
        try:
            selected_text = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected_text:
                start_pos = "1.0"
                while True:
                    start_pos = widget.search(selected_text, start_pos, stopindex=tk.END, exact=True)
                    if not start_pos: break
                    end_pos = f"{start_pos} + {len(selected_text)}c"
                    widget.tag_add("highlight_duplicate", start_pos, end_pos)
                    start_pos = end_pos
        except tk.TclError:
            pass 
            
    def get_format_key(self, name, display_name=False):
        if display_name:
            for key, value in self.format_names.items():
                if value == name: return key
        else:
            return name
        return None
        
    def detect_format(self, content):
        content = content.strip()
        if not content: return None
        if any(line.strip().startswith('//') or '\t' in line or re.search(r'\S {4}\S', line) for line in content.split('\n') if not line.strip().startswith("#")):
            return self.format_names["GalTransl_TSV"]
        if 'gptDict' in content or '[[gptDict]]' in content:
            try:
                toml.loads(content)
                if '[[gptDict]]' in content: return self.format_names["GPPCLI_TOML"]
                return self.format_names["GPPGUI_TOML"]
            except: pass
        if content.startswith('[') and content.endswith(']'):
            try:
                data = json.loads(content)
                if isinstance(data, list) and data and all(k in data[0] for k in ['srt', 'dst', 'info']):
                    return self.format_names["AiNiee_JSON"]
            except: pass
        return None
        
    def parse_tsv_line(self, line):
        line = line.strip()
        if not line or line.startswith(('//', '#')): return None
        parts = re.split(r'\t|(?<=\S) {4}(?=\S)', line)
        parts = [p.strip() for p in parts]
        if len(parts) >= 2:
            return {'org': parts[0], 'rep': parts[1], 'note': parts[2] if len(parts) > 2 else ''}
        return None
        
    def parse_input(self, content, format_display_name):
        format_key = self.get_format_key(format_display_name, display_name=True)
        data = []
        if content.startswith('\ufeff'):
            content = content[1:]
        if not content.strip(): return []

        if format_key == "AiNiee_JSON":
            json_data = json.loads(content)
            for item in json_data: data.append({'org': item.get('srt', ''), 'rep': item.get('dst', ''), 'note': item.get('info', '')})
        elif format_key == "GPPGUI_TOML":
            toml_data = toml.loads(content)
            for item in toml_data.get('gptDict', []): data.append({'org': item.get('org', ''), 'rep': item.get('rep', ''), 'note': item.get('note', '')})
        elif format_key == "GPPCLI_TOML":
            toml_data = toml.loads(content)
            for item in toml_data.get('gptDict', []): data.append({'org': item.get('searchStr', ''), 'rep': item.get('replaceStr', ''), 'note': item.get('note', '')})
        elif format_key == "GalTransl_TSV":
            for line in content.split('\n'):
                parsed = self.parse_tsv_line(line)
                if parsed: data.append(parsed)
        return data
        
    def format_output(self, data, format_key):
        if format_key == "AiNiee_JSON":
            json_data = [{'srt': item['org'], 'dst': item['rep'], 'info': item['note']} for item in data]
            return json.dumps(json_data, ensure_ascii=False, indent=2)
        elif format_key == "GPPGUI_TOML":
            lines = ["gptDict = ["]
            for item in data:
                org = self.escape_toml_string_single(item.get('org',''))
                rep = self.escape_toml_string_single(item.get('rep',''))
                note = self.escape_toml_string_single(item.get('note',''))
                lines.append(f"\t{{ org = '{org}', rep = '{rep}', note = '{note}' }},")
            lines.append("]")
            return "\n".join(lines)
        elif format_key == "GPPCLI_TOML":
            parts = []
            for item in data:
                org = self.escape_toml_string_single(item.get('org',''))
                rep = self.escape_toml_string_single(item.get('rep',''))
                note = self.escape_toml_string_single(item.get('note',''))
                parts.append(f"[[gptDict]]\nnote = '{note}'\nreplaceStr = '{rep}'\nsearchStr = '{org}'")
            return "\n\n".join(parts)
        elif format_key == "GalTransl_TSV":
            return "\n".join([f"{item['org']}\t{item['rep']}" + (f"\t{item['note']}" if item['note'] else "") for item in data])
        return ""
        
    def escape_toml_string_single(self, text):
        return text.replace("'", "''")
        
    def convert(self):
        try:
            input_content = self.input_text.get("1.0", tk.END)
            if not input_content.strip():
                messagebox.showwarning("警告", "请输入要转换的内容")
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

            self.output_text.config(state=tk.NORMAL)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", output_content)
            self._update_all_highlights(self.output_text)
            self.output_text.config(state=tk.DISABLED)
            self.status_var.set(status_msg)

        except Exception as e:
            messagebox.showerror("错误", f"处理失败: {str(e)}")
            self.status_var.set("处理失败")

    def _reformat_current_format(self, content, format_display_name):
        format_key = self.get_format_key(format_display_name, display_name=True)
        if format_key == "GalTransl_TSV":
            return self._reformat_tsv(content)
        if format_key == "GPPGUI_TOML":
            return self._reformat_gppgui_toml(content)
        if format_key == "GPPCLI_TOML":
            return self._reformat_gppcli_toml(content)
        return content

    def _reformat_tsv(self, content):
        new_lines = []
        for line in content.splitlines():
            parsed = self.parse_tsv_line(line)
            if parsed:
                new_line = f"{parsed['org']}\t{parsed['rep']}"
                if parsed['note']:
                    new_line += f"\t{parsed['note']}"
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        return "\n".join(new_lines)

    def _extract_toml_val(self, text, key):
        pattern = rf"{key}\s*=\s*'((?:[^']|'')*)'"
        match = re.search(pattern, text)
        if match:
            return match.group(1).replace("''", "'")
        return None

    def _reformat_gppgui_toml(self, content):
        new_lines = []
        for line in content.splitlines():
            match = re.match(r'^(\s*)(\{.*?\})(\s*,?\s*)(#.*)?$', line)
            if not match:
                new_lines.append(line)
                continue

            leading_ws, entry_text, trailing_part, comment = match.groups()
            comment = comment or ""

            org = self._extract_toml_val(entry_text, 'org')
            rep = self._extract_toml_val(entry_text, 'rep')
            note = self._extract_toml_val(entry_text, 'note')

            if org is not None and rep is not None and note is not None:
                reformatted_entry = "{{ org = '{}', rep = '{}', note = '{}' }}".format(
                    self.escape_toml_string_single(org),
                    self.escape_toml_string_single(rep),
                    self.escape_toml_string_single(note)
                )
                new_lines.append(f"{leading_ws}{reformatted_entry}{trailing_part}{comment}")
            else:
                new_lines.append(line)
        return "\n".join(new_lines)

    def _extract_toml_val_with_comment(self, line, key):
        if line is None: return ('', '')
        pattern = rf"^\s*{key}\s*=\s*'((?:[^']|'')*)'(\s*#.*)?\s*$"
        match = re.match(pattern, line)
        if match:
            val_escaped, comment = match.groups()
            val = val_escaped.replace("''", "'")
            return val, (comment or "")
        return ('', '')

    def _reformat_gppcli_toml(self, content):
        blocks = re.split(r'(\n*\[\[gptDict\]\]\n)', content)
        new_content = [blocks[0]]

        for i in range(1, len(blocks), 2):
            marker = blocks[i]
            block_content = blocks[i+1]
            
            note_line, rep_line, org_line = None, None, None
            other_lines = []

            for line in block_content.splitlines():
                stripped = line.strip()
                if stripped.startswith('note ='): note_line = line
                elif stripped.startswith('replaceStr ='): rep_line = line
                elif stripped.startswith('searchStr ='): org_line = line
                else: other_lines.append(line)

            note_val, note_comment = self._extract_toml_val_with_comment(note_line, 'note')
            rep_val, rep_comment = self._extract_toml_val_with_comment(rep_line, 'replaceStr')
            org_val, org_comment = self._extract_toml_val_with_comment(org_line, 'searchStr')

            new_content.append(marker.strip())

            new_content.append(f"note = '{self.escape_toml_string_single(note_val)}'{note_comment}")
            new_content.append(f"replaceStr = '{self.escape_toml_string_single(rep_val)}'{rep_comment}")
            new_content.append(f"searchStr = '{self.escape_toml_string_single(org_val)}'{org_comment}")
            
            if other_lines:
                new_content.extend(other_lines)

        return "\n".join(new_content)
            
    def open_file(self):
        file_path = filedialog.askopenfilename(
            title="选择文件",
            filetypes=[("所有支持格式", "*.json;*.toml;*.txt"), ("所有文件", "*.*")]
        )
        if not file_path: return
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f: content = f.read()
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", content)
            self.input_text.edit_reset()
            self.current_file_path = file_path
            detected_format = self.detect_format(content)
            if detected_format:
                self.input_format.set(detected_format)
            else:
                self.input_format.set("自动检测")
            self.status_var.set(f"已打开文件: {os.path.basename(file_path)}")
            self._update_all_highlights(self.input_text)
        except Exception as e:
            messagebox.showerror("错误", f"打开文件失败: {str(e)}")
            
    def save_input_file(self):
        input_content = self.input_text.get("1.0", tk.END).strip()
        if not input_content:
            messagebox.showwarning("警告", "输入内容为空，无法保存")
            return

        if self.current_file_path:
            if messagebox.askyesno(
                "确认保存",
                f"是否要覆盖现有文件？\n\n{self.current_file_path}",
                parent=self.root
            ):
                try:
                    with open(self.current_file_path, 'w', encoding='utf-8') as f:
                        f.write(self.input_text.get("1.0", "end-1c"))
                    self.status_var.set(f"文件已覆盖保存: {os.path.basename(self.current_file_path)}")
                except Exception as e:
                    messagebox.showerror("错误", f"保存文件失败: {str(e)}")
                    self.status_var.set("保存失败")
        else:
            original_input_format = self.input_format.get()
            target_format = ""

            if original_input_format == "自动检测":
                detected_format = self.detect_format(input_content)
                if not detected_format:
                    messagebox.showerror("错误", "无法自动检测输入内容的格式，无法保存。请手动指定输入格式。", parent=self.root)
                    return
                target_format = detected_format
                self.input_format.set(detected_format)
            else:
                target_format = original_input_format
            
            self.output_format.set(target_format)
            self.convert()

            if original_input_format == "自动检测":
                self.input_format.set("自动检测")

            self.output_text.config(state=tk.NORMAL)
            output_for_saving = self.output_text.get("1.0", tk.END).strip()
            self.output_text.config(state=tk.DISABLED)

            if output_for_saving:
                self.save_file()
            else:
                self.status_var.set("转换后无内容可保存。")

    def save_file(self):
        self.output_text.config(state=tk.NORMAL)
        output_content = self.output_text.get("1.0", tk.END).strip()
        self.output_text.config(state=tk.DISABLED)
        if not output_content:
            messagebox.showwarning("警告", "没有内容可保存")
            return
            
        output_format_display = self.output_format.get()
        format_key = self.get_format_key(output_format_display, display_name=True)
        default_ext = {
            "AiNiee_JSON": ".json", "GPPGUI_TOML": ".toml", 
            "GPPCLI_TOML": ".toml", "GalTransl_TSV": ".txt"
        }.get(format_key, ".txt")
        
        file_path = filedialog.asksaveasfilename(
            title="保存输出内容", defaultextension=default_ext,
            filetypes=[(f"{output_format_display}", f"*{default_ext}"), ("所有文件", "*.*")]
        )
        if not file_path: return
        try:
            with open(file_path, 'w', encoding='utf-8') as f: f.write(output_content)
            self.status_var.set(f"已保存输出内容: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("错误", f"保存输出内容失败: {str(e)}")
            
    def clear(self):
        self.input_text.delete("1.0", tk.END)
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state=tk.DISABLED)
        self.current_file_path = None
        self.status_var.set("已清空")

def main():
    root = tk.Tk()
    app = GPTDictConverter(root)
    root.mainloop()

if __name__ == "__main__":
    main()