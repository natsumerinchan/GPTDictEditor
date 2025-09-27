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

        self.matches = []
        self.current_match_index = -1
        self.last_find_options = None
        
        self.match_len_var = tk.StringVar()

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.close_dialog)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # 查找
        ttk.Label(main_frame, text="查找:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.find_entry = ttk.Entry(main_frame, width=40)
        self.find_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.find_entry.focus_set()

        # 替换
        ttk.Label(main_frame, text="替换:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.replace_entry = ttk.Entry(main_frame, width=40)
        self.replace_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        # 选项
        option_frame = ttk.Frame(main_frame)
        option_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)
        self.case_var = tk.BooleanVar()
        ttk.Checkbutton(option_frame, text="区分大小写", variable=self.case_var).pack(side=tk.LEFT, padx=5)
        self.regex_var = tk.BooleanVar()
        ttk.Checkbutton(option_frame, text="正则表达式", variable=self.regex_var).pack(side=tk.LEFT, padx=5)

        # 结构化/普通查找切换开关
        self.structured_search_var = tk.BooleanVar(value=True)
        # command=self.toggle_structured_options 联动启用/禁用下面的复选框
        ttk.Checkbutton(option_frame, text="结构化查找替换", variable=self.structured_search_var, command=self.toggle_structured_options).pack(side=tk.LEFT, padx=20)
        
        # 结构化范围
        self.struct_frame = ttk.LabelFrame(main_frame, text="结构化查找替换范围", padding="5")
        self.struct_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        self.in_org_var = tk.BooleanVar(value=True)
        self.in_rep_var = tk.BooleanVar(value=True)
        self.in_note_var = tk.BooleanVar(value=True)
        self.cb_org = ttk.Checkbutton(self.struct_frame, text="原文", variable=self.in_org_var)
        self.cb_org.pack(side=tk.LEFT, padx=10)
        self.cb_rep = ttk.Checkbutton(self.struct_frame, text="译文", variable=self.in_rep_var)
        self.cb_rep.pack(side=tk.LEFT, padx=10)
        self.cb_note = ttk.Checkbutton(self.struct_frame, text="注释", variable=self.in_note_var)
        self.cb_note.pack(side=tk.LEFT, padx=10)

        # 按鈕
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="查找上一个", command=self.find_previous).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="查找下一个", command=self.find_next).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="替换", command=self.replace).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="替换全部", command=self.replace_all).pack(side=tk.LEFT, padx=5)

        self.toggle_structured_options() # 初始化状态

    def toggle_structured_options(self):
        state = tk.NORMAL if self.structured_search_var.get() else tk.DISABLED
        for cb in [self.cb_org, self.cb_rep, self.cb_note]:
            cb.config(state=state)
        self.struct_frame.config(text="结构化查找替换范围" if state == tk.NORMAL else "结构化查找替换 (已禁用)")

    def _get_current_find_options(self):
        # ... (此方法仅用于结构化查找替换)
        return {
            "find_text": self.find_entry.get(), "case": self.case_var.get(),
            "regex": self.regex_var.get(), "in_org": self.in_org_var.get(),
            "in_rep": self.in_rep_var.get(), "in_note": self.in_note_var.get(),
            "content": self.target.get("1.0", tk.END)
        }
    
    # 非结构化查找逻辑，使用 count 参数确保长度准确
    def _perform_plain_find(self, backwards=False):
        self.target.tag_remove('found', '1.0', tk.END)
        find_str = self.find_entry.get()
        if not find_str: return

        try:
            start_pos = self.target.index(tk.SEL_FIRST) if backwards else self.target.index(tk.SEL_LAST)
        except tk.TclError:
            start_pos = self.target.index(tk.INSERT)

        # 使用 self.match_len_var 接收匹配长度，这是最准确的方式
        common_kwargs = {
            "nocase": not self.case_var.get(), 
            "regexp": self.regex_var.get(),
            "count": self.match_len_var
        }
        
        pos = self.target.search(find_str, start_pos, stopindex="1.0" if backwards else tk.END, backwards=backwards, **common_kwargs)
        if not pos: # Wrap search
            wrap_pos = tk.END if backwards else "1.0"
            stop_index = start_pos
            pos = self.target.search(find_str, wrap_pos, stopindex=stop_index, backwards=backwards, **common_kwargs)
            if pos: messagebox.showinfo("提示", "已回绕搜索。", parent=self)

        if pos:
            # 直接从 self.match_len_var 获取准确长度，不再需要重新计算
            match_length = self.match_len_var.get()
            end_pos = f"{pos} + {match_length}c"
            
            self._highlight_match(pos, end_pos)
            self.target.mark_set(tk.INSERT, end_pos if not backwards else pos)
        else:
            messagebox.showinfo("提示", "未找到指定内容", parent=self)

    def _populate_matches(self):
        # (结构化查找替换逻辑)
        self.matches = []
        find_text = self.last_find_options['find_text']
        content = self.last_find_options['content']
        flags = re.IGNORECASE if not self.last_find_options['case'] else 0

        # 移除内容开头的UTF-8 BOM, 避免首行注释判断失效
        if content.startswith('\ufeff'):
            content = content[1:]

        format_key = self.app.get_format_key(self.app.detect_format(content), display_name=True)
        if not format_key: return

        search_fields = [f for f,v in {"org":self.in_org_var,"rep":self.in_rep_var,"note":self.in_note_var}.items() if v.get()]

        try:
            if format_key == "GalTransl_TSV":
                lines = content.split('\n')
                for line_idx, line in enumerate(lines):
                    # ### 改进 ###: 严格跳过注释行
                    if not line.strip() or line.strip().startswith(('//', '#')): continue
                    
                    delimiter_pattern = r'\t|(?<=\S) {4}(?=\S)'
                    delimiters = list(re.finditer(delimiter_pattern, line))
                    
                    def _find_and_add_matches_tsv(text, base_offset):
                        for match in re.finditer(find_text, text, flags):
                            start_pos = f"{line_idx + 1}.{base_offset + match.start()}"
                            end_pos = f"{start_pos} + {len(match.group(0))}c"
                            self.matches.append((start_pos, end_pos, match))

                    if 'org' in search_fields:
                        _find_and_add_matches_tsv(line[0:(delimiters[0].start() if delimiters else len(line))], 0)
                    if 'rep' in search_fields and len(delimiters) >= 1:
                        s, e = delimiters[0].end(), delimiters[1].start() if len(delimiters) >= 2 else len(line)
                        _find_and_add_matches_tsv(line[s:e], s)
                    if 'note' in search_fields and len(delimiters) >= 2:
                        s = delimiters[1].end()
                        _find_and_add_matches_tsv(line[s:], s)
            else: # TOML / JSON
                field_patterns = {
                    'org': r"(?:org|searchStr|srt)\s*=\s*(['\"])((?:(?!\1).|\\.)*?)\1|" + r'"(?:searchStr|srt)"\s*:\s*(")((?:[^"\\]|\\.)*?)\3',
                    'rep': r"(?:rep|replaceStr|dst)\s*=\s*(['\"])((?:(?!\1).|\\.)*?)\1|" + r'"(?:replaceStr|dst)"\s*:\s*(")((?:[^"\\]|\\.)*?)\3',
                    'note': r"(?:note|info)\s*=\s*(['\"])((?:(?!\1).|\\.)*?)\1|" + r'"(?:note|info)"\s*:\s*(")((?:[^"\\]|\\.)*?)\3'
                }

                entry_pattern, field_order = None, []
                if format_key == "GPPGUI_TOML":
                    entry_pattern = r'(\{[\s\S]*?\})'
                    field_order = ['org', 'rep', 'note']
                elif format_key == "GPPCLI_TOML":
                    entry_pattern = r'\[\[gptDict\]\][\s\S]*?(?=\n\[\[gptDict\]\]|\Z)'
                    field_order = ['note', 'rep', 'org']
                elif format_key == "AiNiee_JSON":
                    entry_pattern = r'(\{[\s\S]*?\})'
                    field_order = ['org', 'rep', 'note']

                if not entry_pattern: return
                
                for entry_match in re.finditer(entry_pattern, content):
                    # ### 改进 ###: 严格跳过注释的条目
                    if entry_match.group(0).strip().startswith('#'): continue

                    entry_text, entry_offset = entry_match.group(0), entry_match.start(0)
                    for field in field_order:
                        if field in search_fields:
                            for kv_match in re.finditer(field_patterns[field], entry_text):
                                val_txt, val_start = (kv_match.group(2), kv_match.start(2)) if kv_match.group(2) is not None else (kv_match.group(4), kv_match.start(4))
                                for inner_match in re.finditer(find_text, val_txt, flags):
                                    abs_start = entry_offset + val_start + inner_match.start()
                                    abs_end = entry_offset + val_start + inner_match.end()
                                    start_pos, end_pos = f"1.0 + {abs_start}c", f"1.0 + {abs_end}c"
                                    self.matches.append((start_pos, end_pos, inner_match))
        except re.error as e: messagebox.showerror("正则表达式错误", str(e), parent=self)
        except Exception as e: messagebox.showerror("查找错误", f"结构化查找时发生未知错误: {e}", parent=self)

    def _highlight_match(self, start_pos, end_pos):
        self.target.tag_remove('found', '1.0', tk.END)
        self.target.tag_remove(tk.SEL, "1.0", tk.END)
        self.target.tag_add('found', start_pos, end_pos)
        self.target.tag_add(tk.SEL, start_pos, end_pos)
        self.target.see(start_pos)
        self.target.focus_set()

    def _find_driver(self, direction):
        if not self.structured_search_var.get():
            self._perform_plain_find(backwards=(direction == -1))
            return

        find_options = self._get_current_find_options()
        if not find_options["find_text"]: return

        if self.last_find_options != find_options:
            self.last_find_options = find_options
            self._populate_matches()
            self.current_match_index = -1 if direction == 1 else len(self.matches)

        if not self.matches:
            messagebox.showinfo("提示", "未找到指定内容", parent=self)
            return

        self.current_match_index += direction
        if self.current_match_index >= len(self.matches):
            self.current_match_index = 0
            messagebox.showinfo("提示", "已回绕搜索。", parent=self)
        elif self.current_match_index < 0:
            self.current_match_index = len(self.matches) - 1
            messagebox.showinfo("提示", "已回绕搜索。", parent=self)

        start_pos, end_pos, _ = self.matches[self.current_match_index]
        self._highlight_match(start_pos, end_pos)

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
        if self.structured_search_var.get() and self.regex_var.get():
            if -1 < self.current_match_index < len(self.matches):
                match_obj = self.matches[self.current_match_index][2]
                replace_text = match_obj.expand(replace_text)
        
        self.target.edit_separator()
        self.target.delete(sel_start, sel_end)
        self.target.insert(sel_start, replace_text)
        self.target.edit_separator()
        self.find_next()

    def replace_all(self):
        find_text = self.find_entry.get()
        if not find_text: return
        
        if self.structured_search_var.get():
            self.app.replace_all_structured(
                target_widget=self.target, find_text=find_text, replace_text=self.replace_entry.get(),
                search_in_org=self.in_org_var.get(), search_in_rep=self.in_rep_var.get(), search_in_note=self.in_note_var.get(),
                use_regex=self.regex_var.get(), case_sensitive=self.case_var.get())
        else:
            self.app.replace_all_plain(
                target_widget=self.target, find_text=find_text, replace_text=self.replace_entry.get(),
                use_regex=self.regex_var.get(), case_sensitive=self.case_var.get())

    def close_dialog(self):
        self.target.tag_remove('found', '1.0', tk.END)
        self.destroy()

# #####################################################################
# 主应用程序类
# #####################################################################
class GPTDictConverter:
    def __init__(self, root):
        self.root = root
        self.version = "v1.0.1"
        self.root.title(f"GPT字典编辑转换器   {self.version}")
        self.root.geometry("800x600")
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
        main_frame.columnconfigure(1, weight=1)
        
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(6, weight=1) 
        
        ttk.Label(main_frame, text="输入格式:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.input_format = ttk.Combobox(main_frame, values=["自动检测"] + list(self.format_names.values()), state="readonly", width=25)
        self.input_format.set("自动检测")
        self.input_format.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 20))
        self.input_format.bind("<<ComboboxSelected>>", self._on_input_format_change)
        
        ttk.Label(main_frame, text="输出格式:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_format = ttk.Combobox(main_frame, values=list(self.format_names.values()), state="readonly", width=25)
        self.output_format.set("GalTranslPP GUI TOML格式")
        self.output_format.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 20))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=0, column=2, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=(20, 0))
        
        ttk.Button(button_frame, text="打开文件", command=self.open_file).pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Button(button_frame, text="保存输入内容", command=self.save_input_file).pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Button(button_frame, text="保存输出内容", command=self.save_file).pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Button(button_frame, text="转换", command=self.convert).pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Button(button_frame, text="清空", command=self.clear).pack(side=tk.TOP, fill=tk.X, pady=2)
        
        ttk.Label(main_frame, text="输入内容:").grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        self.input_text = scrolledtext.ScrolledText(
            main_frame, width=80, height=12, undo=True, 
            selectbackground="black", selectforeground="white"
        )
        self.input_text.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        transfer_frame = ttk.Frame(main_frame)
        transfer_frame.grid(row=4, column=0, columnspan=3, pady=2)
        ttk.Button(transfer_frame, text="▲", command=self.transfer_output_to_input).pack()

        output_header_frame = ttk.Frame(main_frame)
        output_header_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5,0))
        ttk.Label(output_header_frame, text="输出内容:").pack(side=tk.LEFT)
        ttk.Button(output_header_frame, text="复制", command=self.copy_output).pack(side=tk.LEFT, padx=10)

        self.output_text = scrolledtext.ScrolledText(
            main_frame, width=80, height=12, undo=True, state=tk.DISABLED,
            selectbackground="black", selectforeground="white"
        )
        self.output_text.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        self._setup_editor_features()
        
    def _on_input_format_change(self, event=None):
        """当手动更改输入格式时，重置文件路径以防意外覆盖。"""
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

        5. 保存结果:
           - 点击“保存输出内容”按钮，将输出内容保存到新文件中。
           - 点击“保存输入内容”按钮，可以直接覆盖保存已打开的文件，
             或者将当前输入框的内容格式化后另存为新文件。

        -------------------------------------------------------------

        其他功能:
        - 清空: 点击“清空”按钮以清除输入和输出框的所有内容。
        - 复制: 点击输出框旁的“复制”按钮，快速复制输出结果。
        - ▲ 按钮: 点击输入框和输出框之间的 ▲ 按钮，可以将当前输出内容
          转移到输入框，方便进行二次编辑或格式转换。
        
        编辑功能 (在输入框中生效):
        - 查找与替换 (快捷键 Ctrl+F):
          - 打开查找与替换对话框。
          - 支持区分大小写、正则表达式、结构化查找等高级功能。
          - 结构化查找: 仅在原文、译文、注释这些
            特定字段内进行查找和替换，避免破坏文件结构。

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
        for widget in widgets:
            widget.tag_configure("key", foreground="#9CDCFE")
            widget.tag_configure("string", foreground="#CE9178")
            widget.tag_configure("punc", foreground="#D4D4D4")
            widget.tag_configure("number", foreground="#B5CEA8")
            widget.tag_configure("comment", foreground="#6A9955")
            widget.tag_configure("tsv_tab", background="#e0f0ff")
            widget.tag_configure("tsv_space_delimiter", background="black", foreground="white")
            widget.tag_configure("highlight_duplicate", background="#555555", foreground="white")
            widget.tag_configure('found', background='darkred', foreground='white')
            widget.bind("<KeyRelease>", self._on_text_change)
            widget.bind("<ButtonRelease-1>", self._on_text_change)
            widget.bind("<Control-slash>", self._toggle_comment)
            widget.bind("<Control-f>", self._show_find_replace_dialog)
        self.highlight_job = None
        
    def _on_text_change(self, event=None):
        if hasattr(self, 'highlight_job') and self.highlight_job:
            self.root.after_cancel(self.highlight_job)
        widget = self.root.focus_get()
        if isinstance(widget, tk.Text):
            self.highlight_job = self.root.after(200, lambda: self._update_all_highlights(widget))
            
    def _update_all_highlights(self, widget):
        self._apply_syntax_highlighting(widget)
        self._highlight_duplicates_on_selection(widget)
        
    def _show_find_replace_dialog(self, event=None):
        target = self.input_text
        FindReplaceDialog(self.root, target, app_instance=self)
        return "break"
    
    def replace_all_plain(self, target_widget, find_text, replace_text, use_regex, case_sensitive):
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

    def replace_all_structured(self, target_widget, find_text, replace_text, 
                               search_in_org, search_in_rep, search_in_note,
                               use_regex, case_sensitive):
        content = target_widget.get("1.0", tk.END)
        format_display_name = self.detect_format(content)
        if not format_display_name:
            messagebox.showerror("错误", "无法自动检测输入内容的格式，无法执行“全部替换”。")
            return

        try:
            data = self.parse_input(content, format_display_name)
            total_replacements = 0
            flags = 0 if case_sensitive else re.IGNORECASE
            
            for item in data:
                fields_to_search = []
                if search_in_org and 'org' in item: fields_to_search.append('org')
                if search_in_rep and 'rep' in item: fields_to_search.append('rep')
                if search_in_note and 'note' in item: fields_to_search.append('note')

                for field in fields_to_search:
                    original_text = item[field]
                    if not original_text: continue

                    if use_regex:
                        new_text, count = re.subn(find_text, replace_text, original_text, flags=flags)
                        if count > 0:
                            item[field] = new_text
                            total_replacements += count
                    else:
                        if case_sensitive:
                            count = original_text.count(find_text)
                            if count > 0:
                                item[field] = original_text.replace(find_text, replace_text)
                                total_replacements += count
                        else:
                            pattern = re.compile(re.escape(find_text), flags)
                            new_text, count = pattern.subn(replace_text, original_text)
                            if count > 0:
                                item[field] = new_text
                                total_replacements += count
            
            if total_replacements == 0:
                messagebox.showinfo("提示", "未找到可替换的内容。")
                return
            
            format_key = self.get_format_key(format_display_name, display_name=True)
            output_content = self.format_output(data, format_key)
            
            target_widget.edit_separator()
            target_widget.delete("1.0", tk.END)
            target_widget.insert("1.0", output_content)
            target_widget.edit_separator()
            self._update_all_highlights(target_widget)
            
            messagebox.showinfo("成功", f"已完成 {total_replacements} 处替换。")
            self.input_format.set(format_display_name)
        except re.error as e:
            messagebox.showerror("正则表达式错误", str(e))
        except Exception as e:
            messagebox.showerror("错误", f"结构化替换失败: {e}")

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
        
        self._update_all_highlights(widget)
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
            input_content = self.input_text.get("1.0", tk.END).strip()
            if not input_content:
                messagebox.showwarning("警告", "请输入要转换的内容")
                return
            input_format, output_format = self.input_format.get(), self.output_format.get()
            if input_format == "自动检测":
                detected_format_display = self.detect_format(input_content)
                if not detected_format_display:
                    raise ValueError("无法自动检测输入内容的格式。")
                self.input_format.set(detected_format_display)
                input_format = detected_format_display

            data = self.parse_input(input_content, input_format)
            output_key = self.get_format_key(output_format, display_name=True)
            output_content = self.format_output(data, output_key)
            self.output_text.config(state=tk.NORMAL)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", output_content)
            self._update_all_highlights(self.output_text)
            self.output_text.config(state=tk.DISABLED)
            self.status_var.set(f"转换完成: {input_format} → {output_format}")
        except Exception as e:
            messagebox.showerror("错误", f"转换失败: {str(e)}")
            self.status_var.set("转换失败")
            
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
                self.input_format.set("自动检测") # 如果识别失败，重置为自动检测
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
                    # 使用 get("1.0", "end-1c") 来避免写入额外的换行符
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

            # 如果原始选择是“自动检测”，转换后恢复，避免锁定到检测到的格式
            if original_input_format == "自动检测":
                self.input_format.set("自动检测")

            self.output_text.config(state=tk.NORMAL)
            output_for_saving = self.output_text.get("1.0", tk.END).strip()
            self.output_text.config(state=tk.DISABLED)

            if output_for_saving:
                self.save_file() # 调用保存输出的函数，弹出另存为对话框
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