"""
该模块定义了 FindReplaceDialog 类，
提供一个用于在文本控件中进行查找和替换操作的对话框。
"""

import re
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox

class FindReplaceDialog(ttk.Toplevel):
    """
    一个用于查找和替换文本的 Toplevel 窗口。
    它可以在目标文本控件中高亮所有匹配项，并执行替换操作，
    支持VS Code风格的正则表达式替换和多行匹配。
    """
    def __init__(self, master, target_widget, app_instance):
        super().__init__(master)
        self.transient(master)
        self.title("查找与替换（仅限输入框）")
        
        self.target = target_widget
        self.app = app_instance
        
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.close_dialog)
        
        self.find_entry.focus_set()

    def create_widgets(self):
        """创建并布局对话框中的所有UI组件。"""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill=BOTH)

        ttk.Label(main_frame, text="查找:").grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.find_entry = ttk.Combobox(main_frame, width=40, values=self.app.find_history)
        self.find_entry.grid(row=0, column=1, columnspan=2, sticky=(W, E), padx=5, pady=5)

        ttk.Label(main_frame, text="替换:").grid(row=1, column=0, sticky=W, padx=5, pady=5)
        self.replace_entry = ttk.Combobox(main_frame, width=40, values=self.app.replace_history)
        self.replace_entry.grid(row=1, column=1, columnspan=2, sticky=(W, E), padx=5, pady=5)

        option_frame = ttk.Frame(main_frame)
        option_frame.grid(row=2, column=0, columnspan=3, sticky=W, pady=5)
        self.case_var = tk.BooleanVar()
        ttk.Checkbutton(option_frame, text="区分大小写", variable=self.case_var, bootstyle="primary").pack(side=LEFT, padx=5)
        self.regex_var = tk.BooleanVar()
        ttk.Checkbutton(option_frame, text="正则表达式", variable=self.regex_var, bootstyle="primary").pack(side=LEFT, padx=5)

        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.grid(row=3, column=0, columnspan=3, sticky=W, padx=5, pady=2)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="查找上一个", command=self.find_previous, bootstyle="secondary").pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="查找下一个", command=self.find_next, bootstyle="secondary").pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="替换", command=self.replace, bootstyle="primary").pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="替换全部", command=self.replace_all, bootstyle="danger").pack(side=LEFT, padx=5)

        self.find_entry.bind('<KeyRelease>', lambda e: self._highlight_all_matches())
        self.case_var.trace_add('write', lambda *a: self._highlight_all_matches())
        self.regex_var.trace_add('write', lambda *a: self._highlight_all_matches())
    
    def _find_all_matches(self) -> list:
        """在目标控件中查找所有匹配项，并返回它们的索引。"""
        find_str = self.find_entry.get()
        if not find_str:
            return []

        case = self.case_var.get()
        regex = self.regex_var.get()
        content = self.target.get('1.0', tk.END)
        matches = []

        try:
            if regex:
                # [修正] 添加 re.MULTILINE 标志
                flags = re.MULTILINE
                if not case:
                    flags |= re.IGNORECASE
                
                for m in re.finditer(find_str, content, flags):
                    start_idx = self.target.index(f"1.0 + {m.start()} chars")
                    end_idx = self.target.index(f"1.0 + {m.end()} chars")
                    matches.append({'start': start_idx, 'end': end_idx})
            else:
                search_content = content if case else content.lower()
                search_str = find_str if case else find_str.lower()
                start_char_index = 0
                while True:
                    start_char_index = search_content.find(search_str, start_char_index)
                    if start_char_index == -1: break
                    end_char_index = start_char_index + len(find_str)
                    start_idx = self.target.index(f"1.0 + {start_char_index} chars")
                    end_idx = self.target.index(f"1.0 + {end_char_index} chars")
                    matches.append({'start': start_idx, 'end': end_idx})
                    start_char_index = end_char_index
        except re.error as e:
            self.status_label.config(text=f"正则表达式错误: {e}")
            return []
        
        return matches

    def _highlight_all_matches(self, focus_index: int | None = None):
        """根据查找结果更新文本控件中的高亮标签。"""
        self.target.tag_remove('found', '1.0', tk.END)
        self.target.tag_remove('found_current', '1.0', tk.END)

        matches = self._find_all_matches()
        if not matches:
            self.status_label.config(text="0 / 0")
            return

        for match in matches:
            self.target.tag_add('found', match['start'], match['end'])

        current_match_index = 0
        if focus_index is not None and focus_index < len(matches):
            current_match_index = focus_index
        else:
            cursor_pos = self.target.index(tk.INSERT)
            for i, match in enumerate(matches):
                if self.target.compare(cursor_pos, '>=', match['start']) and \
                   self.target.compare(cursor_pos, '<', match['end']):
                    current_match_index = i
                    break
        
        if matches:
            current_match = matches[current_match_index]
            self.target.tag_add('found_current', current_match['start'], current_match['end'])
            self.target.see(current_match['start'])
            self.status_label.config(text=f"{current_match_index + 1} / {len(matches)}")
        
        self.target.tag_config('found', background='#ffeeba')
        self.target.tag_config('found_current', background='#ff9800')

    def _find_next_match_index(self, current_index, backwards, num_matches):
        """计算下一个匹配项的索引。"""
        if num_matches == 0:
            return -1
        if backwards:
            return (current_index - 1 + num_matches) % num_matches
        else:
            return (current_index + 1) % num_matches

    def _perform_find(self, backwards=False):
        """执行查找操作的核心逻辑。"""
        find_term = self.find_entry.get()
        if find_term and find_term not in self.app.find_history:
            self.app.find_history.insert(0, find_term)
            self.find_entry['values'] = self.app.find_history
            
        matches = self._find_all_matches()
        if not matches:
            messagebox.showinfo("提示", "未找到指定内容", parent=self)
            return

        cursor_pos = self.target.index(tk.INSERT)
        
        current_match_index = -1
        # 查找光标当前所在的匹配项
        for i, match in enumerate(matches):
            if self.target.compare(cursor_pos, '>=', match['start']) and \
               self.target.compare(cursor_pos, '<', match['end']):
                current_match_index = i
                break
        
        # 如果光标不在任何匹配项内，根据查找方向确定下一个
        if current_match_index == -1:
            if backwards:
                # 从后往前找第一个起始位置在光标前的
                for i in range(len(matches) - 1, -1, -1):
                    if self.target.compare(cursor_pos, '>', matches[i]['start']):
                        current_match_index = i
                        break
                # 如果没找到（光标在所有匹配项之前），则从最后一个开始，这样-1后就是倒数第二个
                if current_match_index == -1: 
                    current_match_index = 0
            else:
                # 从前往后找第一个起始位置在光标后的
                for i, match in enumerate(matches):
                    if self.target.compare(cursor_pos, '<=', match['start']):
                        # 我们希望从这个匹配项开始，所以将当前索引设置为它之前的一个
                        current_match_index = i - 1
                        break
                # 如果循环结束还没找到，说明光标在最后一个匹配之后, 准备从头开始
                else:
                    current_match_index = len(matches) - 1
        
        next_match_index = self._find_next_match_index(current_match_index, backwards, len(matches))

        if next_match_index != -1:
            match_to_show = matches[next_match_index]
            self.target.see(match_to_show['start'])
            # see之后立即更新，否则光标位置可能不正确
            self.target.update_idletasks() 
            # 将光标移动到新匹配项的开头，并选中它
            self.target.tag_remove(tk.SEL, "1.0", tk.END)
            self.target.mark_set(tk.INSERT, match_to_show['start'])
            self.target.tag_add(tk.SEL, match_to_show['start'], match_to_show['end'])
            self._highlight_all_matches(focus_index=next_match_index)
        else:
            messagebox.showinfo("提示", "未找到指定内容", parent=self)

    def find_next(self):
        """查找下一个匹配项。"""
        self._perform_find(backwards=False)

    def find_previous(self):
        """查找上一个匹配项。"""
        self._perform_find(backwards=True)

    def _python_style_repl(self, repl: str):
        """
        将替换字符串从VS Code风格($1)转换为Python风格(\\1)，
        以便re.sub/subn可以原生处理所有Python正则替换语法，
        包括命名捕获组 \\g<name>。
        """
        # 将 $1, $2 ... 转换为 \1, \2 ...
        # 使用一个函数来替换，避免替换$10时错误地匹配$1
        s = re.sub(r'\$(\d+)', r'\\\1', repl)
        return s

    def replace(self):
        """替换当前选中的匹配项，并自动查找下一个。"""
        find_term = self.find_entry.get()
        if find_term and find_term not in self.app.find_history:
            self.app.find_history.insert(0, find_term)
            self.find_entry['values'] = self.app.find_history
            
        replace_term = self.replace_entry.get()
        if replace_term and replace_term not in self.app.replace_history:
            self.app.replace_history.insert(0, replace_term)
            self.replace_entry['values'] = self.app.replace_history

        if not self.target.tag_ranges(tk.SEL):
            self.find_next()
            if not self.target.tag_ranges(tk.SEL):
                return

        sel_start = self.target.index(tk.SEL_FIRST)
        sel_end = self.target.index(tk.SEL_LAST)
        original_text = self.target.get(sel_start, sel_end)
        
        self.target.edit_separator()
        
        if self.regex_var.get():
            find_str = self.find_entry.get()
            replace_str = self.replace_entry.get()
            case = self.case_var.get()
            
            # [修正] 添加 re.MULTILINE 标志
            flags = re.MULTILINE
            if not case:
                flags |= re.IGNORECASE
            
            # 获取Python风格的替换字符串
            py_replace_str = self._python_style_repl(replace_str)
            new_text = re.sub(find_str, py_replace_str, original_text, count=1, flags=flags)
            self.target.delete(sel_start, sel_end)
            self.target.insert(sel_start, new_text)
        else:
            replace_text = self.replace_entry.get()
            self.target.delete(sel_start, sel_end)
            self.target.insert(sel_start, replace_text)
            
        self.target.edit_separator()
        self.find_next()

    def replace_all(self):
        """替换所有匹配项。"""
        find_text = self.find_entry.get()
        if find_text and find_text not in self.app.find_history:
            self.app.find_history.insert(0, find_text)
            self.find_entry['values'] = self.app.find_history

        replace_text = self.replace_entry.get()
        if replace_text and replace_text not in self.app.replace_history:
            self.app.replace_history.insert(0, replace_text)
            self.replace_entry['values'] = self.app.replace_history
            
        if not find_text:
            return
        
        content = self.target.get('1.0', tk.END)
        case = self.case_var.get()
        regex = self.regex_var.get()
        
        try:
            if regex:
                # [修正] 添加 re.MULTILINE 标志
                flags = re.MULTILINE
                if not case:
                    flags |= re.IGNORECASE
                
                # 获取Python风格的替换字符串
                py_replace_str = self._python_style_repl(replace_text)
                new_content, total_count = re.subn(find_text, py_replace_str, content, flags=flags)
            else:
                if not case:
                    flags = re.IGNORECASE
                    new_content, total_count = re.subn(re.escape(find_text), replace_text, content, flags=flags)
                else:
                    total_count = content.count(find_text)
                    new_content = content.replace(find_text, replace_text)
        except re.error as e:
            self.status_label.config(text=f"正则表达式错误: {e}")
            messagebox.showerror("正则表达式错误", str(e), parent=self)
            return

        if total_count > 0:
            self.target.edit_separator()
            self.target.set_content(new_content, reset_modified_flag=False)
            self.target.edit_separator()
            self._highlight_all_matches()
            self.status_label.config(text=f"已完成 {total_count} 处替换。")
            messagebox.showinfo("成功", f"已完成 {total_count} 处替换。", parent=self)
        else:
            self.status_label.config(text="未找到可替换的内容。")
            messagebox.showinfo("提示", "未找到可替换的内容。", parent=self)

    def close_dialog(self):
        """关闭对话框时，清除所有高亮标记。"""
        self.target.tag_remove('found', '1.0', tk.END)
        self.target.tag_remove('found_current', '1.0', tk.END)
        self.destroy()