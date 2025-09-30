# utils/settings.py
import json
from pathlib import Path

SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
    "geometry": "1000x600",
    "last_directory": str(Path.home()),
    "auto_convert": True,
}

def load_settings():
    """
    加载JSON配置文件。
    如果文件不存在或格式错误，则返回默认设置。
    """
    settings_path = Path(SETTINGS_FILE)
    if not settings_path.exists():
        return DEFAULT_SETTINGS
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
            # 确保所有默认键都存在，防止配置文件不完整
            for key, value in DEFAULT_SETTINGS.items():
                settings.setdefault(key, value)
            return settings
    except (json.JSONDecodeError, IOError):
        return DEFAULT_SETTINGS

def save_settings(settings):
    """
    将设置字典保存到JSON文件。
    """
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except IOError as e:
        print(f"警告: 无法保存设置文件到 {SETTINGS_FILE}。错误: {e}")
