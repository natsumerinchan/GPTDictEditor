# #####################################################################
# 1. 依赖检查与导入
# #####################################################################
import sys
from tkinter import messagebox, Tk

# 尝试导入核心依赖，如果失败则提供明确的错误信息
try:
    from tkinterdnd2 import TkinterDnD
except ImportError:
    # 使用一个临时的Tk窗口来显示错误消息
    root = Tk()
    root.withdraw()
    messagebox.showerror(
        "缺少依赖",
        "错误: 缺少 'tkinterdnd2' 包。\n"
        "此包用于实现拖放文件功能。\n\n"
        "请在命令行运行以下命令进行安装:\n"
        "pip install tkinterdnd2"
    )
    sys.exit(1)

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