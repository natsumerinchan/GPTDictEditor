"""
该模块定义了 GoToLineDialog 类，
提供一个用于跳转到指定文本行号的对话框。
"""

import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox

class GoToLineDialog(ttk.Toplevel):
    """
    一个用于跳转到指定行的 Toplevel 窗口。
    用户可以选择目标是输入框还是输出框。
    """
    def __init__(self, master, app_instance):
        """
        初始化跳转到行对话框。
        
        Args:
            master: 父控件 (主窗口)。
            app_instance: 主应用程序的实例，用于访问文本编辑器控件。
        """
        super().__init__(master)
        self.app = app_instance
        
        # 窗口基本设置
        self.transient(master)
        self.title("跳转到行")
        self.geometry("280x150")
        self.resizable(False, False)
        
        self.create_widgets()
        
        # 确保窗口关闭时正确销毁
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        
        # 设置为模态对话框，阻止与其他窗口交互
        self.grab_set()

    def create_widgets(self):
        """创建并布局对话框中的所有UI组件。"""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill=BOTH)

        # 行号输入区域
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=X, pady=5)
        ttk.Label(input_frame, text="行号:").pack(side=LEFT, padx=(0, 5))
        self.line_entry = ttk.Entry(input_frame)
        self.line_entry.pack(side=LEFT, expand=True, fill=X)
        self.line_entry.focus_set()  # 自动聚焦到输入框
        self.line_entry.bind("<Return>", self.on_ok)  # 绑定回车键

        # 目标选择区域 (输入框/输出框)
        target_frame = ttk.Frame(main_frame)
        target_frame.pack(pady=5)
        self.target_var = tk.StringVar(value="input")
        ttk.Radiobutton(
            target_frame, text="输入框", variable=self.target_var, value="input", bootstyle="primary"
        ).pack(side=LEFT, padx=5)
        ttk.Radiobutton(
            target_frame, text="输出框", variable=self.target_var, value="output", bootstyle="primary"
        ).pack(side=LEFT, padx=5)

        # 操作按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="确定", command=self.on_ok, bootstyle="primary").pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy, bootstyle="secondary").pack(side=LEFT, padx=5)

    def on_ok(self, event=None):
        """
        处理“确定”按钮的点击事件或回车键。
        验证输入，并执行跳转操作。
        """
        line_str = self.line_entry.get()
        target_choice = self.target_var.get()
        
        # 根据用户的选择确定目标文本控件
        target_widget = self.app.input_text if target_choice == "input" else self.app.output_text

        # 验证行号是否为有效数字
        try:
            line_num = int(line_str)
        except ValueError:
            messagebox.showerror("错误", "请输入一个有效的数字。", parent=self)
            return

        # 验证行号是否在有效范围内
        total_lines_str = target_widget.index('end-1c').split('.')[0]
        total_lines = int(total_lines_str) if total_lines_str else 0
        if not (1 <= line_num <= total_lines):
            messagebox.showerror("错误", f"行号必须在 1 到 {total_lines} 之间。", parent=self)
            return

        # 特殊处理：如果目标控件被禁用（如输出框），需先启用再操作
        # 注意：状态操作必须指向内部的 .text 组件
        was_disabled = (target_widget.text.cget("state") == DISABLED)
        if was_disabled:
            target_widget.text.config(state=NORMAL)

        # 移除之前可能存在的所有行高亮
        for widget in [self.app.input_text, self.app.output_text]:
            widget.tag_remove("goto_line", "1.0", tk.END)
        
        # 添加高亮，移动光标，并滚动视图
        target_widget.tag_add("goto_line", f"{line_num}.0", f"{line_num}.end")
        target_widget.mark_set(tk.INSERT, f"{line_num}.0")
        target_widget.see(f"{line_num}.0")
        target_widget.focus_set()

        # 如果控件之前是禁用的，操作完成后重新禁用它
        if was_disabled:
            # 使用 after 确保UI更新后再禁用
            target_widget.after(100, lambda: target_widget.text.config(state=tk.DISABLED))

        # 关闭对话框
        self.destroy()