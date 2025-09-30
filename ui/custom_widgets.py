"""
该模块包含自定义的Tkinter控件。
目前，它定义了一个带行号的文本编辑器组件。
"""

import tkinter as tk
from tkinter import ttk

class EditorWithLineNumbers(tk.Frame):
    """
    一个组合了文本框、行号画布和滚动条的自定义Tkinter控件。
    """
    def __init__(self, master, *args, **kwargs):
        """
        初始化带行号的编辑器。
        
        Args:
            master: 父控件。
            *args, **kwargs: 传递给内部 tk.Text 控件的参数。
        """
        super().__init__(master)
        
        # 从kwargs中提取字体，如果未提供则使用默认值
        self.text_font = kwargs.get('font', ("Consolas", 10))
        
        # 配置网格布局
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # 创建行号画布
        self.linenumbers = tk.Canvas(self, width=40, background="#f0f0f0", highlightthickness=0)
        self.linenumbers.grid(row=0, column=0, sticky="ns")

        # 创建垂直滚动条
        self.vbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.yview)
        self.vbar.grid(row=0, column=2, sticky="ns")
        
        # 创建水平滚动条
        self.hbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL)
        self.hbar.grid(row=1, column=1, sticky="ew")

        # 创建核心文本控件
        self.text = tk.Text(self, undo=True, wrap=tk.NONE, *args, **kwargs)
        self.text.grid(row=0, column=1, sticky="nsew")
        
        # 将滚动条与文本控件关联
        self.text.config(yscrollcommand=self.on_text_scroll, xscrollcommand=self.hbar.set)
        self.hbar.config(command=self.text.xview)

        # 绑定事件以追踪文本变化和视图变化
        self.text.bind("<<Modified>>", self._on_change_proxy)
        self.text.bind("<Configure>", self._on_change_proxy)

        self._redraw_job = None
        self.is_modified_flag = False

    def on_text_scroll(self, first, last):
        """当文本框滚动时，同步滚动条和行号。"""
        self.vbar.set(first, last)
        self.linenumbers.yview_moveto(first)
        self.redraw_line_numbers()

    def yview(self, *args):
        """处理来自垂直滚动条的滚动命令。"""
        self.text.yview(*args)
        self.linenumbers.yview(*args)
        self.redraw_line_numbers()
        return "break"

    def _on_change_proxy(self, event=None):
        """
        文本内容或配置更改时的代理处理程序。
        它会延迟重绘行号以优化性能。
        """
        if self.text.edit_modified():
            self.is_modified_flag = True
            # 必须重置标记，否则<<Modified>>事件不会再次触发
            self.text.edit_modified(False)

        # 使用 after() 来延迟行号重绘，避免在快速输入时卡顿
        if self._redraw_job:
            self.after_cancel(self._redraw_job)
        self._redraw_job = self.after(50, self.redraw_line_numbers)

    def redraw_line_numbers(self):
        """重绘行号画布上的所有行号。"""
        self.linenumbers.delete("all")
        try:
            # 获取总行数以动态调整行号区域的宽度
            total_lines_str = self.text.index('end-1c').split('.')[0]
            line_count = int(total_lines_str) if total_lines_str else 1
            new_width = 25 + len(total_lines_str) * 8
            if self.linenumbers.winfo_width() != new_width:
                self.linenumbers.config(width=new_width)

            # 获取当前光标所在行，以便高亮显示
            current_line_num = self.text.index(tk.INSERT).split('.')[0]
            
            # 遍历可见区域的行并绘制行号
            i = self.text.index("@0,0")
            while True:
                dline = self.text.dlineinfo(i)
                if dline is None: break
                
                y = dline[1]
                linenum_str = i.split('.')[0]
                # 高亮当前行号
                color = "#1e1e1e" if linenum_str == current_line_num else "#858585"
                self.linenumbers.create_text(
                    new_width - 8, y, anchor=tk.NE, text=linenum_str, fill=color, font=self.text_font
                )
                i = self.text.index(f"{i}+1line")
        except (tk.TclError, ValueError):
            # 在某些边缘情况下（如文本框被清空时），可能会发生TclError，安全地忽略它
            pass

    def get_content(self) -> str:
        """获取文本框的全部内容。"""
        return self.text.get("1.0", "end-1c")

    def set_content(self, content: str, reset_modified_flag: bool = True):
        """
        设置文本框的内容，并可选择重置修改状态。
        
        Args:
            content: 要设置的文本内容。
            reset_modified_flag: 如果为True，则清除撤销历史和修改标记。
        """
        is_disabled = self.text.cget("state") == tk.DISABLED
        if is_disabled: self.text.config(state=tk.NORMAL)
        
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        
        if reset_modified_flag:
            self.text.edit_reset()
            self.is_modified_flag = False
            
        if is_disabled: self.text.config(state=tk.DISABLED)

    def clear(self):
        """清空文本框内容并重置修改状态。"""
        self.set_content("", reset_modified_flag=True)

    def config(self, cnf=None, **kw):
        """
        重写 config 方法以将配置选项正确分派给 Frame 或 Text 控件。
        """
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
        """
        属性代理。如果在此类中找不到某个属性，
        则尝试从内部的 self.text 控件中获取它。
        这使得我们可以直接在 EditorWithLineNumbers 实例上调用 Text 的方法，
        例如 editor.tag_add(...)。
        """
        try:
            return getattr(self.text, name)
        except AttributeError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")