# #####################################################################
# 1. 依赖检查与导入
# #####################################################################
import sys
import ttkbootstrap as ttk
from tkinter import messagebox
from tkinterdnd2 import TkinterDnD

# 从其他模块导入主应用程序类
from app import GPTDictConverter

# #####################################################################
# 2. 主函数
# #####################################################################
def main():
    """
    应用程序的主入口函数。
    - 初始化TkinterDnD窗口。
    - 创建GPTDictConverter应用实例。
    - 启动Tkinter事件循环。
    """
    try:
        # 使用 TkinterDnD.Tk() 作为根窗口以启用拖放功能
        root = TkinterDnD.Tk()
        
        # 实例化主应用程序
        style = ttk.Style()
        app = GPTDictConverter(root)
        
        # 启动UI事件循环
        root.mainloop()

    except Exception as e:
        # 捕获意外的全局错误并在退出前显示
        messagebox.showerror("意外错误", f"应用程序遇到严重错误，即将退出。\n\n错误详情: {e}")
        sys.exit(1)

# #####################################################################
# 3. 脚本执行入口
# #####################################################################
if __name__ == "__main__":
    main()