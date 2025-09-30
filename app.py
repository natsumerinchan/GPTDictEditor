# #####################################################################
# 1. 依赖检查与导入
# #####################################################################

# 标准库导入
import os
import sys
import tkinter as tk
import tkinter.font as tkFont
import webbrowser
import json
from tkinter import ttk, messagebox
from typing import Optional

import markdown
from tkhtmlview import HTMLScrolledText
import toml


# 从项目模块导入
from constants import APP_VERSION, FORMAT_DEFINITIONS
from ui.custom_widgets import EditorWithLineNumbers
from ui.dialogs.find_replace import FindReplaceDialog
from ui.dialogs.go_to_line import GoToLineDialog
from core import conversion, syntax
from utils import file_io

# #####################################################################
# 2. 主应用程序类
# #####################################################################
class GPTDictConverter:
    """
    GPT字典编辑转换器的主应用程序类。
    负责UI的创建、事件处理和模块协调。
    """
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"GPT字典编辑转换器   {APP_VERSION}")
        self.root.geometry("1000x600")
        self.root.protocol("WM_DELETE_WINDOW", self.ask_quit)
        
        # 初始化状态变量
        self.APP_VERSION = APP_VERSION
        self.current_file_path: Optional[str] = None
        self.last_directory: str = os.path.expanduser("~")
        
        # 从常量中提取格式名称用于UI
        self.format_names = {k: v["name"] for k, v in FORMAT_DEFINITIONS.items()}
        
        # 实例化辅助模块
        self.syntax_handler = syntax.SyntaxHandler(self)
        self.file_handler = file_io.FileHandler(self)

        # 创建UI组件
        self._create_menu()
        self._create_widgets()
        
        # 设置编辑器功能和拖放
        self.syntax_handler.setup_editor_features()
        self.file_handler.setup_dnd()


    def _create_widgets(self):
        """创建应用程序的主窗口组件。"""
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
        
        # --- 输入格式 ---
        ttk.Label(format_frame, text="输入格式:").pack(anchor=tk.W)
        self.input_format = ttk.Combobox(format_frame, values=["自动检测"] + list(self.format_names.values()), state="readonly", width=25)
        self.input_format.set("自动检测")
        self.input_format.pack(pady=2)
        
        # --- 输出格式 [修正] ---
        # 下面这两行是之前缺失或错误放置的代码
        ttk.Label(format_frame, text="输出格式:").pack(anchor=tk.W, pady=(5, 0))
        self.output_format = ttk.Combobox(format_frame, values=list(self.format_names.values()), state="readonly", width=25)
        self.output_format.set(self.format_names["GPPGUI_TOML"])
        self.output_format.pack(pady=2)
        self.output_format.bind("<<ComboboxSelected>>", self.auto_convert)

        # --- 按钮区域 ---
        button_frame = ttk.Frame(top_control_frame)
        button_frame.pack(side=tk.LEFT, padx=20, anchor='n')
        
        btn_grid = ttk.Frame(button_frame)
        btn_grid.pack()
        ttk.Button(btn_grid, text="打开文件", command=self.file_handler.open_file).grid(row=0, column=0, padx=5, pady=2)
        ttk.Button(btn_grid, text="保存输入", command=self.file_handler.save_input_file).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(btn_grid, text="保存输出", command=self.file_handler.save_output_file).grid(row=0, column=2, padx=5, pady=2)
        ttk.Button(btn_grid, text="转换", command=self.convert).grid(row=1, column=0, padx=5, pady=2)
        ttk.Button(btn_grid, text="清空", command=self.clear).grid(row=1, column=1, padx=5, pady=2)
        
        self.auto_convert_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(button_frame, text="打开文件时自动转换", variable=self.auto_convert_var).pack(pady=5)
        
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

        # --- 编辑器共享样式 ---
        editor_style = {
            "font": ("Consolas", 10), "background": "#FFFFFF", "foreground": "#000000",
            "insertbackground": "black", "selectbackground": "#ADD6FF", "selectforeground": "black",
            "inactiveselectbackground": "#E5E5E5", "insertwidth": 2, "padx": 5, "pady": 5,
        }
        self.input_text.config(**editor_style)
        self.output_text.config(**editor_style)

    def _create_menu(self):
        """创建应用程序的顶部菜单栏。"""
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
        
        self.root.bind_all("<Control-f>", self._show_find_replace_dialog)
        self.root.bind_all("<Control-g>", self._show_goto_line_dialog)

    def convert(self):
        """执行格式转换。"""
        try:
            input_content = self.input_text.get_content()
            if not input_content.strip():
                self.output_text.clear()
                self.status_var.set("输入为空，已清空输出。")
                return

            input_format_display = self.input_format.get()
            output_format_display = self.output_format.get()
            
            if input_format_display == "自动检测":
                detected_format = conversion.detect_format(input_content)
                if not detected_format:
                    raise ValueError("无法自动检测输入内容的格式。")
                self.input_format.set(detected_format)
                input_format_display = detected_format

            if input_format_display == output_format_display:
                output_content = conversion.reformat_content(input_content, input_format_display)
                status_msg = f"格式化完成: {input_format_display}"
            else:
                input_key = conversion.get_format_key(input_format_display, display_name=True)
                output_key = conversion.get_format_key(output_format_display, display_name=True)
                if not input_key or not output_key:
                    raise ValueError("无效的格式选择。")
                
                data = conversion.parse_input(input_content, input_key)
                output_content = conversion.format_output(data, output_key)
                status_msg = f"转换完成: {input_format_display} → {output_format_display}"

            self.output_text.set_content(output_content, reset_modified_flag=True)
            self.syntax_handler.update_all_highlights(self.output_text)
            self.status_var.set(status_msg)

        except (ValueError, json.JSONDecodeError, toml.TomlDecodeError) as e:
            messagebox.showerror("处理失败", str(e))
            self.status_var.set(f"处理失败: {e}")
        except Exception as e:
            messagebox.showerror("未知错误", f"发生未知错误: {str(e)}")
            self.status_var.set("发生未知错误")

    def auto_convert(self, event=None):
        if self.auto_convert_var.get():
            self.convert()
            
    def clear(self):
        self.input_text.clear()
        self.output_text.clear()
        self.current_file_path = None
        self.input_format.set("自动检测")
        self.status_var.set("已清空")
        self.root.title(f"GPT字典编辑转换器   {self.APP_VERSION}")

    def transfer_output_to_input(self):
        output_content = self.output_text.get_content()
        if not output_content:
            self.status_var.set("输出内容为空，无法传递。")
            return
        
        self.input_text.set_content(output_content)
        self.input_format.set(self.output_format.get())
        self.current_file_path = None
        self.syntax_handler.update_all_highlights(self.input_text)
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

    def ask_quit(self):
        if self.input_text.is_modified_flag:
            if messagebox.askyesno("退出确认", "输入内容已被修改但未保存，确定要退出吗？"):
                self.root.destroy()
        else:
            self.root.destroy()

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
        about_win.geometry("420x240"); about_win.resizable(False, False)
        main_frame = ttk.Frame(about_win, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)
        ttk.Label(main_frame, text="GPT字典编辑转换器", font=("", 12, "bold")).pack(pady=(0, 10))
        ttk.Label(main_frame, text=f"版本: {self.APP_VERSION}").pack(pady=2)
        link_font = tkFont.Font(family="Helvetica", size=10, underline=True)
        author_frame = ttk.Frame(main_frame); author_frame.pack(pady=2)
        ttk.Label(author_frame, text="作者: ").pack(side=tk.LEFT)
        author_link = ttk.Label(author_frame, text="natsumerinchan", foreground="blue", cursor="hand2", font=link_font)
        author_link.pack(side=tk.LEFT)
        author_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/natsumerinchan"))
        license_frame = ttk.Frame(main_frame); license_frame.pack(pady=2)
        ttk.Label(license_frame, text="开源许可证: ").pack(side=tk.LEFT)
        license_link = ttk.Label(license_frame, text="MIT License", foreground="blue", cursor="hand2", font=link_font)
        license_link.pack(side=tk.LEFT)
        license_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/natsumerinchan/GPTDictEditor/blob/master/LICENSE"))
        repo_link = ttk.Label(main_frame, text="https://github.com/natsumerinchan/GPTDictEditor", foreground="blue", cursor="hand2", font=link_font)
        repo_link.pack(pady=10)
        repo_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/natsumerinchan/GPTDictEditor"))
        ttk.Button(main_frame, text="确定", command=about_win.destroy).pack(pady=15)
        about_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - about_win.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - about_win.winfo_height()) // 2
        about_win.geometry(f"+{x}+{y}")
        about_win.focus_set(); about_win.grab_set()
    
    def _show_help_dialog(self):
        help_win = tk.Toplevel(self.root)
        help_win.title("使用教程"); help_win.transient(self.root); help_win.geometry("700x600")
        try:
            help_md_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "./docs/help.md")
            with open(help_md_path, "r", encoding="utf-8") as f: help_text_md = f.read()
        except Exception as e:
            help_text_md = f"# 帮助文档加载失败\n\n无法读取 help.md 文件：{e}"
        main_frame = ttk.Frame(help_win, padding=10); main_frame.pack(expand=True, fill=tk.BOTH)
        html_content = markdown.markdown(help_text_md, extensions=['fenced_code', 'tables'])
        html_text = HTMLScrolledText(main_frame, background="white"); html_text.pack(expand=True, fill=tk.BOTH)
        html_text.set_html(html_content)
        button_frame = ttk.Frame(help_win, padding=(0, 0, 0, 10)); button_frame.pack(fill=tk.X)
        ttk.Button(button_frame, text="关闭", command=help_win.destroy).pack()
        help_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - help_win.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - help_win.winfo_height()) // 2
        help_win.geometry(f"+{x}+{y}")
        help_win.focus_set(); help_win.grab_set()