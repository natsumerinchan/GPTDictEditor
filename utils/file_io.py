"""
该模块封装了所有与文件输入/输出相关的操作，
包括打开、保存和处理拖放事件。
"""

import os
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES

# 从项目模块导入
from constants import FORMAT_DEFINITIONS
from core import conversion

class FileHandler:
    """
    一个处理所有文件操作的类，包括读写和拖放。
    """
    def __init__(self, app_instance):
        """
        初始化文件处理器。

        Args:
            app_instance: 主应用程序 GPTDictConverter 的实例。
        """
        self.app = app_instance

    def setup_dnd(self):
        """设置输入文本框的拖放功能。"""
        self.app.input_text.drop_target_register(DND_FILES)
        self.app.input_text.dnd_bind('<<Drop>>', self.on_drop)

    def on_drop(self, event):
        """
        处理文件拖放到输入框的事件。
        
        Args:
            event: 拖放事件对象。
        """
        # event.data 通常是带有花括号的文件路径，需要清理
        file_path = event.data.strip('{}')
        if os.path.isfile(file_path):
            self._open_file_path(file_path)

    def open_file(self):
        """
        显示文件选择对话框，并加载用户选择的文件。
        """
        file_path = filedialog.askopenfilename(
            title="选择文件",
            initialdir=self.app.last_directory,
            filetypes=[
                ("所有支持格式", "*.json;*.toml;*.txt"),
                ("JSON 文件", "*.json"),
                ("TOML 文件", "*.toml"),
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.app.last_directory = os.path.dirname(file_path) # 记忆上次打开的目录
            self._open_file_path(file_path)

    def _open_file_path(self, file_path: str):
        """
        根据给定的路径加载文件内容到输入框。

        Args:
            file_path: 要打开的文件的完整路径。
        """
        if not file_path: return
        
        try:
            # 使用 'utf-8-sig' 编码来自动处理可能存在的BOM头
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            
            self.app.input_text.set_content(content, reset_modified_flag=True)
            self.app.current_file_path = file_path
            
            # 自动检测格式并更新UI
            detected_format_name = conversion.detect_format(content)
            self.app.input_format.set(detected_format_name if detected_format_name else "自动检测")
            
            # 更新状态栏和窗口标题
            self.app.status_var.set(f"已打开: {os.path.basename(file_path)}")
            self.app.root.title(f"GPT字典编辑转换器   {self.app.APP_VERSION}   [已打开 {file_path} ]")
            
            # 触发语法高亮和自动转换
            self.app.syntax_handler.update_all_highlights(self.app.input_text)
            self.app.auto_convert()
            
        except Exception as e:
            messagebox.showerror("错误", f"打开文件失败: {str(e)}")
            self.app.status_var.set(f"打开失败: {e}")
            self.app.root.title(f"GPT字典编辑转换器   {self.app.APP_VERSION}")

    def save_input_file(self):
        """保存输入框中的内容到文件。"""
        content = self.app.input_text.get_content()
        if not content:
            messagebox.showwarning("警告", "输入内容为空，无法保存")
            return

        # 如果当前已打开文件，则默认保存到该文件，否则弹出另存为对话框
        save_path = self.app.current_file_path
        if not save_path:
            save_path = self._get_save_path(is_input=True)
        
        if not save_path:
            self.app.status_var.set("保存已取消")
            return

        # 写入文件
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.app.last_directory = os.path.dirname(save_path)
            self.app.current_file_path = save_path
            self.app.input_text.edit_reset() # 清除撤销历史
            self.app.input_text.is_modified_flag = False
            
            # 更新UI
            self.app.status_var.set(f"文件已保存: {save_path}")
            self.app.root.title(f"GPT字典编辑转换器   {self.app.APP_VERSION} [已打开 {save_path} ]")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存文件失败: {str(e)}")
            self.app.status_var.set("保存失败")

    def save_output_file(self):
        """保存输出框中的内容到文件。"""
        output_content = self.app.output_text.get_content()
        if not output_content:
            messagebox.showwarning("警告", "输出内容为空，无法保存")
            return

        save_path = self._get_save_path(is_input=False)
        if not save_path:
            self.app.status_var.set("保存已取消")
            return

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(output_content)
            self.app.last_directory = os.path.dirname(save_path)
            self.app.status_var.set(f"已保存输出: {os.path.basename(save_path)}")
        except Exception as e:
            messagebox.showerror("错误", f"保存输出内容失败: {str(e)}")

    def _get_save_path(self, is_input: bool) -> str:
        """
        根据是保存输入还是输出来配置并显示“另存为”对话框。

        Args:
            is_input: 如果为True，则为输入框配置；否则为输出框配置。

        Returns:
            用户选择的文件路径，如果取消则返回空字符串。
        """
        if is_input:
            title = "保存输入内容"
            content = self.app.input_text.get_content()
            format_display_name = self.app.input_format.get()
            if format_display_name == "自动检测":
                detected = conversion.detect_format(content)
                if detected: format_display_name = detected
        else:
            title = "保存输出内容"
            format_display_name = self.app.output_format.get()

        format_key = conversion.get_format_key(format_display_name, display_name=True)
        default_ext = FORMAT_DEFINITIONS.get(format_key, {}).get("ext", ".txt")
        file_types = [(f"{format_display_name}", f"*{default_ext}"), ("所有文件", "*.*")]
        
        initial_file = None
        # 为输出文件生成一个建议的文件名
        if not is_input and self.app.current_file_path:
            base, _ = os.path.splitext(os.path.basename(self.app.current_file_path))
            initial_file = base + default_ext

        return filedialog.asksaveasfilename(
            title=title,
            initialdir=self.app.last_directory,
            initialfile=initial_file,
            defaultextension=default_ext,
            filetypes=file_types
        )