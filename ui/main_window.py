# ui/main_window.py
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from .custom_widgets import EditorWithLineNumbers
from constants import EDITOR_STYLE

class MainWindowUI:
    """负责主窗口UI的创建和布局。"""
    def __init__(self, app):
        self.app = app
        self.root = app.root

        self._create_menu()
        self._create_widgets()

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
        format_frame.pack(side=LEFT, padx=10)
        
        # --- 输入格式 ---
        ttk.Label(format_frame, text="输入格式:").pack(anchor=W)
        self.app.input_format = ttk.Combobox(format_frame, values=["自动检测"] + list(self.app.format_names.values()), state="readonly", width=25)
        self.app.input_format.set("自动检测")
        self.app.input_format.pack(pady=2)
        
        # --- 输出格式 ---
        ttk.Label(format_frame, text="输出格式:").pack(anchor=W, pady=(5, 0))
        self.app.output_format = ttk.Combobox(format_frame, values=list(self.app.format_names.values()), state="readonly", width=25)
        self.app.output_format.set(self.app.format_names["GPPGUI_TOML"])
        self.app.output_format.pack(pady=2)
        self.app.output_format.bind("<<ComboboxSelected>>", self.app.auto_convert)

        # --- 按钮区域 ---
        button_frame = ttk.Frame(top_control_frame)
        button_frame.pack(side=LEFT, padx=20, anchor='n')
        
        btn_grid = ttk.Frame(button_frame)
        btn_grid.pack()
        ttk.Button(btn_grid, text="打开文件", command=self.app.file_handler.open_file, bootstyle="primary").grid(row=0, column=0, padx=5, pady=2)
        ttk.Button(btn_grid, text="保存输入", command=self.app.file_handler.save_input_file, bootstyle="success").grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(btn_grid, text="保存输出", command=self.app.file_handler.save_output_file, bootstyle="success").grid(row=0, column=2, padx=5, pady=2)
        ttk.Button(btn_grid, text="转换", command=self.app.convert, bootstyle="info").grid(row=1, column=0, padx=5, pady=2)
        ttk.Button(btn_grid, text="清空", command=self.app.clear, bootstyle="danger").grid(row=1, column=1, padx=5, pady=2)
        
        self.app.auto_convert_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(button_frame, text="打开文件时自动转换", variable=self.app.auto_convert_var, bootstyle="primary").pack(pady=5)
        
        # --- 内容编辑区 ---
        content_frame = ttk.PanedWindow(main_frame, orient=HORIZONTAL)
        content_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")

        input_pane = ttk.Frame(content_frame)
        input_header = ttk.Frame(input_pane)
        input_header.pack(fill=X, pady=(0, 5))
        ttk.Label(input_header, text="输入内容 (可拖入文件):").pack(side=LEFT, anchor=W)
        ttk.Button(input_header, text="复制", command=self.app.copy_input, bootstyle="info-outline").pack(side=LEFT, padx=10)
        self.app.input_text = EditorWithLineNumbers(input_pane, borderwidth=1, relief="solid")
        self.app.input_text.pack(expand=True, fill=BOTH)
        
        output_pane = ttk.Frame(content_frame)
        output_header = ttk.Frame(output_pane)
        output_header.pack(fill=X, pady=(0, 5))
        ttk.Label(output_header, text="输出内容:").pack(side=LEFT, anchor=W)
        ttk.Button(output_header, text="复制", command=self.app.copy_output, bootstyle="info-outline").pack(side=LEFT, padx=10)
        ttk.Button(output_header, text="传至输入栏", command=self.app.transfer_output_to_input, bootstyle="warning-outline").pack(side=LEFT)
        self.app.output_text = EditorWithLineNumbers(output_pane, state=DISABLED, borderwidth=1, relief="solid")
        self.app.output_text.pack(expand=True, fill=BOTH)

        content_frame.add(input_pane, weight=1)
        content_frame.add(output_pane, weight=1)
        
        # --- 状态栏 ---
        self.app.status_var = tk.StringVar(value="就绪")
        ttk.Label(main_frame, textvariable=self.app.status_var, relief=SUNKEN).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 0))

        # --- 编辑器共享样式 ---
        self.app.input_text.config(**EDITOR_STYLE)
        self.app.output_text.config(**EDITOR_STYLE)

        # 从设置恢复“自动转换”复选框的状态
        self.app.auto_convert_var.set(self.app.settings.get("auto_convert", True))

    def _create_menu(self):
        """创建应用程序的顶部菜单栏。"""
        self.app.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.app.menu_bar)
        
        edit_menu = tk.Menu(self.app.menu_bar, tearoff=0)
        self.app.menu_bar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="查找与替换 (Ctrl+F)", command=self.app._show_find_replace_dialog)
        edit_menu.add_command(label="跳转到行... (Ctrl+G)", command=self.app._show_goto_line_dialog)
        
        help_menu = tk.Menu(self.app.menu_bar, tearoff=0)
        self.app.menu_bar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用教程", command=self.app.show_help_dialog)
        
        about_menu = tk.Menu(self.app.menu_bar, tearoff=0)
        self.app.menu_bar.add_cascade(label="关于", menu=about_menu)
        about_menu.add_command(label="关于本软件", command=self.app.show_about_dialog)
        
        self.root.bind_all("<Control-f>", self.app._show_find_replace_dialog)
        self.root.bind_all("<Control-g>", self.app._show_goto_line_dialog)
