# #####################################################################
# 1. 依赖检查与导入
# #####################################################################

# 标准库导入
import os
import sys
from pathlib import Path
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter.font as tkFont
import webbrowser
import json
from tkinter import messagebox
from typing import Optional

import markdown
from tkhtmlview import HTMLScrolledText
import toml


# 从项目模块导入
from constants import APP_VERSION, FORMAT_DEFINITIONS
from ui.main_window import MainWindowUI
from ui.custom_widgets import EditorWithLineNumbers
from ui.dialogs.find_replace import FindReplaceDialog
from ui.dialogs.go_to_line import GoToLineDialog
from ui.dialogs import about_dialog, help_dialog
from core import conversion, syntax
from utils import file_io, settings

# #####################################################################
# 2. 主应用程序类
# #####################################################################
class GPTDictConverter:
    """
    GPT字典编辑转换器的主应用程序类。
    负责UI的创建、事件处理和模块协调。
    """
    def __init__(self, root: ttk.Window):
        self.root = root
        self.root.title(f"GPT字典编辑转换器   {APP_VERSION}")
        
        # 加载设置
        self.settings = settings.load_settings()
        
        self.root.geometry(self.settings.get("geometry", "1000x600"))
        self.root.protocol("WM_DELETE_WINDOW", self.ask_quit)
        
        # 初始化状态变量
        self.APP_VERSION = APP_VERSION
        self.current_file_path: Optional[str] = None
        self.last_directory: str = self.settings.get("last_directory", str(Path.home()))
        
        # 初始化查找替换历史
        self.find_history = []
        self.replace_history = []
        
        
        # 从常量中提取格式名称用于UI
        self.format_names = {k: v["name"] for k, v in FORMAT_DEFINITIONS.items()}
        
        # 实例化辅助模块
        self.syntax_handler = syntax.SyntaxHandler(self)
        self.file_handler = file_io.FileHandler(self)

        # 实例化UI构建器
        self.ui = MainWindowUI(self)
        
        # 设置编辑器功能和拖放
        self.syntax_handler.setup_editor_features()
        self.file_handler.setup_dnd()

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
            self.output_text.clear() # 转换失败时清空输出
        except Exception as e:
            messagebox.showerror("未知错误", f"发生未知错误: {str(e)}")
            self.status_var.set("发生未知错误")
            self.output_text.clear() # 转换失败时清空输出

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
        """退出前确认并保存设置。"""
        if self.input_text.is_modified_flag:
            if not messagebox.askyesno("退出确认", "输入内容已被修改但未保存，确定要退出吗？"):
                return

        # 保存当前设置
        current_settings = {
            "geometry": self.root.winfo_geometry(),
            "last_directory": self.last_directory,
            "auto_convert": self.auto_convert_var.get(),
        }
        settings.save_settings(current_settings)
        
        self.root.destroy()

    def _show_find_replace_dialog(self, event=None):
        FindReplaceDialog(self.root, self.input_text, app_instance=self)
        return "break"
    
    def _show_goto_line_dialog(self, event=None):
        GoToLineDialog(self.root, app_instance=self)
        return "break"

    def show_about_dialog(self):
        """显示关于对话框。"""
        about_dialog.show_about_dialog(self.root, self.APP_VERSION)
    
    def show_help_dialog(self):
        """显示帮助对话框。"""
        help_dialog.show_help_dialog(self.root)