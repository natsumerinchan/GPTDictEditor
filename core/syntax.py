"""
该模块负责处理编辑器的语法高亮和交互式编辑功能。
"""

import re
import tkinter as tk
from tkinterdnd2 import DND_FILES # 导入DND_FILES以备将来使用
from ui.custom_widgets import EditorWithLineNumbers
from constants import HIGHLIGHT_DELAY_MS
# 导入 conversion 模块以使用其辅助函数
from core import conversion

class SyntaxHandler:
    """
    一个管理编辑器语法高亮、快捷键和事件绑定的类。
    """
    def __init__(self, app_instance):
        """
        初始化语法处理器。

        Args:
            app_instance: 主应用程序 GPTDictConverter 的实例。
        """
        self.app = app_instance
        self.highlight_job_id: str | None = None

    def setup_editor_features(self):
        """
        为应用程序中的所有编辑器配置样式、标签和事件绑定。
        """
        # 统一配置标签颜色
        tag_colors = {
            "key": "#A31515",  # JSON/TOML的键，深红色
            "string": "#0000FF",  # 字符串，蓝色
            "number": "#098658",  # 数字，绿色
            "boolean_null": "#0000FF",  # 布尔/null，蓝色
            "punc": "#000000",
            "comment": "#008000",  # 注释，绿色
            "tsv_tab": {"background": "#E0E8F0"},
            "tsv_space_delimiter": {"background": "#E0E8F0"},
            "highlight_duplicate": {"background": "#B4D5FF"},
            "found": {"background": "#FFD700"},  # 查找对话框使用
            "found_current": {"background": "#ff9800"},  # 查找对话框使用
            "goto_line": {"background": "#FFFACD"},  # 跳转对话框使用
        }
        
        widgets = [self.app.input_text, self.app.output_text]
        for widget in widgets:
            # 应用所有标签配置
            for tag, props in tag_colors.items():
                if isinstance(props, dict):
                    widget.tag_configure(tag, **props)
                else:
                    widget.tag_configure(tag, foreground=props)
            
            # 为每个文本框的内部Text组件绑定划词高亮事件
            widget.text.bind("<<Selection>>", self.on_selection_change)

        # 只对输入框绑定修改和注释相关的事件
        self.app.input_text.text.bind("<KeyRelease>", self.on_text_change)
        self.app.input_text.text.bind("<Control-slash>", self.toggle_comment)
        
        # 绑定输入格式下拉框的变更事件
        self.app.input_format.bind("<<ComboboxSelected>>", self.on_input_format_change)

    # -------------------------------------------------------------
    # 事件处理
    # -------------------------------------------------------------
    def on_text_change(self, event=None):
        """处理文本输入事件，延迟触发语法高亮。"""
        widget = self.app.input_text
        widget.tag_remove("goto_line", "1.0", tk.END) # 清除跳转高亮
        
        if self.highlight_job_id:
            self.app.root.after_cancel(self.highlight_job_id)
            
        self.highlight_job_id = self.app.root.after(
            HIGHLIGHT_DELAY_MS, lambda: self.update_all_highlights(widget)
        )
        
    def on_selection_change(self, event=None):
        """处理文本选择事件，高亮显示重复项。"""
        if not event: return

        # event.widget 是内部的 tk.Text 组件，我们需要找到它的 EditorWithLineNumbers 父容器
        source_widget = event.widget
        parent_editor = source_widget
        while parent_editor and not isinstance(parent_editor, EditorWithLineNumbers):
            parent_editor = parent_editor.master
        
        if parent_editor:
            self._highlight_duplicates_on_selection(parent_editor)
        
    def on_input_format_change(self, event=None):
        """处理输入格式下拉框的变更事件。"""
        if self.app.current_file_path:
            self.app.current_file_path = None
            self.app.status_var.set("输入格式已更改，文件关联已重置。")
            self.app.root.title(f"GPT字典编辑转换器   {self.app.APP_VERSION}")

        self.update_all_highlights(self.app.input_text)

    # -------------------------------------------------------------
    # 语法高亮核心逻辑
    # -------------------------------------------------------------
    def update_all_highlights(self, widget: EditorWithLineNumbers):
        """
        更新指定编辑器的所有高亮效果（语法和重复项）。

        Args:
            widget: 目标 EditorWithLineNumbers 实例。
        """
        self._apply_syntax_highlighting(widget)
        self._highlight_duplicates_on_selection(widget)

    def _get_active_format_key(self, widget: EditorWithLineNumbers) -> str | None:
        """根据编辑器和当前UI状态确定其内容的格式键。"""
        content = widget.get_content()
        if widget == self.app.input_text:
            format_name = self.app.input_format.get()
            if format_name == "自动检测":
                detected_display_name = conversion.detect_format(content)
                return conversion.get_format_key(detected_display_name, display_name=True) if detected_display_name else None
            return conversion.get_format_key(format_name, display_name=True)
        else: # output_text
            return conversion.get_format_key(self.app.output_format.get(), display_name=True)
    
    def _apply_syntax_highlighting(self, widget: EditorWithLineNumbers):
        """对指定的编辑器应用语法高亮。"""
        # 清除旧的语法标签
        all_tags = ["key", "string", "punc", "comment", "tsv_tab", "tsv_space_delimiter", "number", "boolean_null"]
        for tag in all_tags:
            widget.tag_remove(tag, "1.0", tk.END)
        
        format_key = self._get_active_format_key(widget)
        if not format_key: return
        
        content = widget.get_content()
        
        # 定义不同格式的词法规则
        token_specs = {
            'BASE': [
                ('COMMENT', r'#.*$'),
                ('STRING', r'"([^"\\]*(?:\\.[^"\\]*)*)"'),
                ('NUMBER', r'\b-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?\b'),
                ('BOOLEAN_NULL', r'\b(true|false|null)\b'),
                ('PUNC', r'[\[\]{},=:]'),
            ],
            'GPPGUI_TOML': [('KEY', r'\b(org|rep|note)\b(?=\s*=)')],
            'GPPCLI_TOML': [('KEY', r'\b(note|replaceStr|searchStr)\b(?=\s*=)')],
            # 匹配 JSON 中所有在冒号前的键
            'AiNiee_JSON': [('KEY', r'"([^"\\]*(?:\\.[^"\\]*)*)"(?=\s*:)')],
            'GalTransl_TSV': [
                ('COMMENT', r'//.*$'),
                ('TSV_TAB', r'\t'),
                ('TSV_SPACE_DELIMITER', r'(?<=\S) {4}(?=\S)'),
            ]
        }
        
        # 根据格式选择正确的规则集
        # 将特定格式的规则放在前面，以保证更高的匹配优先级
        specific_specs = token_specs.get(format_key, [])
        base_specs = token_specs['BASE']
        
        if format_key == 'GalTransl_TSV':
            current_specs = specific_specs
        else:
            current_specs = specific_specs + base_specs

        try:
            tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in current_specs)
        except re.error as e:
            self.app.status_var.set(f"语法高亮错误: {e}")
            return
        
        # 遍历所有匹配项并应用标签
        for mo in re.finditer(tok_regex, content, re.MULTILINE):
            kind = mo.lastgroup
            start, end = f"1.0 + {mo.start()} chars", f"1.0 + {mo.end()} chars"
            
            tag_map = {
                'KEY': 'key', 'STRING': 'string', 'PUNC': 'punc', 'COMMENT': 'comment',
                'TSV_TAB': 'tsv_tab', 'TSV_SPACE_DELIMITER': 'tsv_space_delimiter',
                'NUMBER': 'number', 'BOOLEAN_NULL': 'boolean_null'
            }
            if kind in tag_map:
                widget.tag_add(tag_map[kind], start, end)

    def _highlight_duplicates_on_selection(self, widget: EditorWithLineNumbers):
        """高亮显示与当前选中内容相同的其他文本。"""
        widget.tag_remove("highlight_duplicate", "1.0", tk.END)
        try:
            selected_text = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            # 仅当选中文本有意义时才执行搜索
            if selected_text and len(selected_text.strip()) > 1:
                start_pos = "1.0"
                while True:
                    start_pos = widget.search(selected_text, start_pos, stopindex=tk.END, exact=True)
                    if not start_pos: break
                    # 不高亮选中区域本身
                    if start_pos == widget.index(tk.SEL_FIRST):
                        start_pos = widget.index(tk.SEL_LAST)
                        continue
                    end_pos = f"{start_pos} + {len(selected_text)}c"
                    widget.tag_add("highlight_duplicate", start_pos, end_pos)
                    start_pos = end_pos
        except tk.TclError:
            # 如果没有选择任何内容，tk.SEL_FIRST 会引发 TclError，安全地忽略它
            pass

    # -------------------------------------------------------------
    # 编辑器交互
    # -------------------------------------------------------------
    def toggle_comment(self, event):
        """根据当前格式为选中行添加或移除注释。"""
        widget = self.app.input_text
        format_key = self._get_active_format_key(widget)
        
        # 确定不同格式的注释符号
        comment_char_map = {"GPPGUI_TOML": "#", "GPPCLI_TOML": "#", "GalTransl_TSV": "//"}
        comment_char = comment_char_map.get(format_key)
        
        if not comment_char: return "break"
        
        try:
            sel_start_index = widget.index(tk.SEL_FIRST)
            sel_end_index = widget.index(tk.SEL_LAST)
            start_line = int(sel_start_index.split('.')[0])
            end_line = int(sel_end_index.split('.')[0])
            # 如果选区的结尾在第0列，不应处理结尾索引所在的新行
            if int(sel_end_index.split('.')[1]) == 0:
                end_line -= 1
        except tk.TclError:
            # 如果没有选区，则只处理光标当前所在的行
            start_line = end_line = int(widget.index(tk.INSERT).split('.')[0])
        
        if end_line < start_line: return "break"

        widget.edit_separator()
        lines = [widget.get(f"{i}.0", f"{i}.end") for i in range(start_line, end_line + 1)]
        non_empty_lines = [line for line in lines if line.strip()]
        if not non_empty_lines:
            widget.edit_separator()
            return "break"
        
        # 判断是该注释还是取消注释
        all_commented = all(line.strip().startswith(comment_char) for line in non_empty_lines)

        for i in range(start_line, end_line + 1):
            line_content = widget.get(f"{i}.0", f"{i}.end")
            if not line_content.strip(): continue

            if all_commented:
                # 取消注释
                idx = line_content.find(comment_char)
                if idx != -1:
                    # 如果注释符后跟了一个空格，也一并删除
                    end_offset = idx + len(comment_char)
                    if line_content[end_offset:].startswith(' '):
                        end_offset += 1
                    widget.delete(f"{i}.{idx}", f"{i}.{end_offset}")
            else:
                # 添加注释
                widget.insert(f"{i}.0", f"{comment_char} ")
        
        widget.edit_separator()
        self.update_all_highlights(widget)
        return "break" # 阻止事件进一步传播