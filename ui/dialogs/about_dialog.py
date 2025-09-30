import tkinter as tk
import tkinter.font as tkFont
import webbrowser
from tkinter import ttk

def show_about_dialog(parent, app_version):
    """显示“关于”对话框。"""
    about_win = tk.Toplevel(parent)
    about_win.title("关于")
    about_win.transient(parent)
    about_win.geometry("420x240")
    about_win.resizable(False, False)
    
    main_frame = ttk.Frame(about_win, padding="15")
    main_frame.pack(expand=True, fill=tk.BOTH)
    
    ttk.Label(main_frame, text="GPT字典编辑转换器", font=("", 12, "bold")).pack(pady=(0, 10))
    ttk.Label(main_frame, text=f"版本: {app_version}").pack(pady=2)
    
    link_font = tkFont.Font(family="Helvetica", size=10, underline=True)
    
    author_frame = ttk.Frame(main_frame)
    author_frame.pack(pady=2)
    ttk.Label(author_frame, text="作者: ").pack(side=tk.LEFT)
    author_link = ttk.Label(author_frame, text="natsumerinchan", foreground="blue", cursor="hand2", font=link_font)
    author_link.pack(side=tk.LEFT)
    author_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/natsumerinchan"))
    
    license_frame = ttk.Frame(main_frame)
    license_frame.pack(pady=2)
    ttk.Label(license_frame, text="开源许可证: ").pack(side=tk.LEFT)
    license_link = ttk.Label(license_frame, text="MIT License", foreground="blue", cursor="hand2", font=link_font)
    license_link.pack(side=tk.LEFT)
    license_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/natsumerinchan/GPTDictEditor/blob/master/LICENSE"))
    
    repo_link = ttk.Label(main_frame, text="https://github.com/natsumerinchan/GPTDictEditor", foreground="blue", cursor="hand2", font=link_font)
    repo_link.pack(pady=10)
    repo_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/natsumerinchan/GPTDictEditor"))
    
    ttk.Button(main_frame, text="确定", command=about_win.destroy).pack(pady=15)
    
    about_win.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() - about_win.winfo_width()) // 2
    y = parent.winfo_y() + (parent.winfo_height() - about_win.winfo_height()) // 2
    about_win.geometry(f"+{x}+{y}")
    about_win.focus_set()
    about_win.grab_set()
