import tkinter as tk
from tkinter import ttk
from pathlib import Path

import markdown
from tkhtmlview import HTMLScrolledText

def show_help_dialog(parent):
    """显示“帮助”对话框。"""
    help_win = tk.Toplevel(parent)
    help_win.title("使用教程")
    help_win.transient(parent)
    help_win.geometry("700x600")
    
    try:
        # 使用 pathlib 定位 help.md
        base_dir = Path(__file__).resolve().parent
        help_md_path = base_dir / "../../docs/help.md"
        with open(help_md_path, "r", encoding="utf-8") as f:
            help_text_md = f.read()
    except Exception as e:
        help_text_md = f"# 帮助文档加载失败\n\n无法读取 help.md 文件：{e}"
        
    main_frame = ttk.Frame(help_win, padding=10)
    main_frame.pack(expand=True, fill=tk.BOTH)
    
    html_content = markdown.markdown(help_text_md, extensions=['fenced_code', 'tables'])
    
    html_text = HTMLScrolledText(main_frame, background="white")
    html_text.pack(expand=True, fill=tk.BOTH)
    html_text.set_html(html_content)
    
    button_frame = ttk.Frame(help_win, padding=(0, 0, 0, 10))
    button_frame.pack(fill=tk.X)
    ttk.Button(button_frame, text="关闭", command=help_win.destroy).pack()
    
    help_win.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() - help_win.winfo_width()) // 2
    y = parent.winfo_y() + (parent.winfo_height() - help_win.winfo_height()) // 2
    help_win.geometry(f"+{x}+{y}")
    help_win.focus_set()
    help_win.grab_set()
