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
        self.find_entry = ttk.Entry(main_frame, width=40)
        self.find_entry.grid(row=0, column=1, columnspan=2, sticky=(W, E), padx=5, pady=5)

        ttk.Label(main_frame, text="替换:").grid(row=1, column=0, sticky=W, padx=5, pady=5)
        self.replace_entry = ttk.Entry(main_frame, width=40)
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

    def _perform_find(self, backwards=False):
        """执行查找操作的核心逻辑。"""
        matches = self._find_all_matches()
        if not matches:
            messagebox.showinfo("提示", "未找到指定内容", parent=self)
            return

        cursor_pos = self.target.index(tk.INSERT)
        
        current_match_index = -1
        for i, match in enumerate(matches):
             if self.target.compare(cursor_pos, '>', match['start']) and \
                self.target.compare(cursor_pos, '<=', match['end']):
                current_match_index = i
                break

        if backwards:
            next_match_index = (current_match_index - 1 + len(matches)) % len(matches)
        else:
            if current_match_index != -1:
                 next_match_index = (current_match_index + 1) % len(matches)
            else:
                next_match_index = 0
                for i, match in enumerate(matches):
                    if self.target.compare(match['start'], '>=', cursor_pos):
                        next_match_index = i
                        break

        self._highlight_all_matches(focus_index=next_match_index)
        
        match_to_select = matches[next_match_index]
        self.target.tag_remove(tk.SEL, '1.0', tk.END)
        self.target.tag_add(tk.SEL, match_to_select['start'], match_to_select['end'])
        self.target.mark_set(tk.INSERT, match_to_select['end'])
        self.target.see(match_to_select['start'])

    def find_next(self):
        self._perform_find(backwards=False)

    def find_previous(self):
        self._perform_find(backwards=True)

    def _vscode_style_repl(self, repl: str):
        """返回一个可用于re.sub/subn的替换函数。"""
        def _repl(m: re.Match) -> str:
            s = repl
            for i in range(1, 100):
                group_val = m.group(i) if m.lastindex and i <= m.lastindex else ""
                s = s.replace(f"${i}", group_val if group_val is not None else "")

            def _esc(m2: re.Match) -> str:
                code = m2.group(1)
                if code == 'r': return '\r'
                if code == 'n': return '\n'
                if code == 't': return '\t'
                if code == 'b': return '\b'
                if code == 'f': return '\f'
                if code == '\\': return '\\'
                if code == '$': return '$'
                if code.startswith('u') and len(code) == 5:
                    try: return chr(int(code[1:], 16))
                    except Exception: return m2.group(0)
                if code.startswith('x') and len(code) == 3:
                    try: return chr(int(code[1:], 16))
                    except Exception: return m2.group(0)
                return m2.group(0)

            return re.sub(r'\\(r|n|t|b|f|\\|\$|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2})', _esc, s)
        return _repl

    def replace(self):
        """替换当前选中的匹配项，并自动查找下一个。"""
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
            
            replacer = self._vscode_style_repl(replace_str)
            new_text = re.sub(find_str, replacer, original_text, count=1, flags=flags)
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
        if not find_text:
            return
        
        replace_text = self.replace_entry.get()
        content = self.target.get('1.0', tk.END)
        case = self.case_var.get()
        regex = self.regex_var.get()
        
        try:
            if regex:
                # [修正] 添加 re.MULTILINE 标志
                flags = re.MULTILINE
                if not case:
                    flags |= re.IGNORECASE
                    
                replacer = self._vscode_style_repl(replace_text)
                new_content, total_count = re.subn(find_text, replacer, content, flags=flags)
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