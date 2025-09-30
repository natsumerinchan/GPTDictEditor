"""
该模块负责所有与数据格式转换相关的核心逻辑。
它与UI完全解耦，只处理数据和文本。
"""

import json
import re
from typing import List, Dict, Optional

# 尝试导入 toml，如果失败则提供明确的错误信息
try:
    import toml
except ImportError:
    # 在模块级别抛出异常，因为这是核心功能的硬性要求
    raise ImportError(
        "错误：缺少 'toml' 包。\n"
        "请在命令行运行以下命令进行安装：\n"
        "pip install toml"
    )

# 从项目模块导入常量
from constants import FORMAT_DEFINITIONS

# 定义标准化的内部数据结构类型别名
DictEntry = Dict[str, str]
DictData = List[DictEntry]

def get_format_key(name: str, display_name: bool = False) -> Optional[str]:
    """
    根据格式的显示名称或内部键名查找其内部键名。

    Args:
        name: 格式的名称 (可以是显示名称或内部键)。
        display_name: 如果为True，则表示 'name' 是一个显示名称。

    Returns:
        如果找到，则返回格式的内部键名 (如 "GPPGUI_TOML")，否则返回None。
    """
    if display_name:
        for key, value in FORMAT_DEFINITIONS.items():
            if value["name"] == name:
                return key
        return None
    
    return name if name in FORMAT_DEFINITIONS else None

def detect_format(content: str) -> Optional[str]:
    """
    根据文件内容自动检测其格式。

    Args:
        content: 文件的文本内容。

    Returns:
        如果检测成功，返回格式的显示名称，否则返回None。
    """
    content = content.strip()
    if not content:
        return None

    # 1. 优先判断 TOML 格式
    # 检查 TOML 特有的关键字和结构
    if 'gptDict' in content or '[[gptDict]]' in content or content.startswith('gptDict'):
        try:
            toml.loads(content)
            if '[[gptDict]]' in content:
                return FORMAT_DEFINITIONS["GPPCLI_TOML"]["name"]
            return FORMAT_DEFINITIONS["GPPGUI_TOML"]["name"]
        except toml.TomlDecodeError:
            # 即使关键字匹配，如果解析失败，也不将其识别为 TOML
            pass
            
    # 2. 判断 TSV 格式
    # 检查是否存在制表符、特定数量的空格分隔符或TSV风格的注释
    tsv_like = False
    lines = content.split('\n')[:20] # 只检查前20行以提高性能
    for line in lines:
        l = line.strip()
        if l.startswith('#') or l.startswith('[gptDict]'):
            continue  # 忽略可能是TOML的行
        if l.startswith('//') or '\t' in l or re.search(r'\S {4}\S', l):
            tsv_like = True
            break
    if tsv_like:
        return FORMAT_DEFINITIONS["GalTransl_TSV"]["name"]

    # 3. 判断 JSON 格式
    # 检查是否为JSON数组结构，并验证其中元素的字段
    if content.startswith('[') and content.endswith(']'):
        try:
            data = json.loads(content)
            if isinstance(data, list) and data and all(k in data[0] for k in ['src', 'dst']):
                return FORMAT_DEFINITIONS["AiNiee_JSON"]["name"]
        except json.JSONDecodeError:
            pass
            
    return None

def parse_input(content: str, format_key: str) -> DictData:
    """
    将给定格式的文本内容解析为标准的内部数据结构。

    Args:
        content: 输入的文本内容。
        format_key: 内容的格式键名 (如 "GPPGUI_TOML")。

    Returns:
        一个包含字典条目的列表。
    
    Raises:
        ValueError: 如果格式键无效或解析失败。
    """
    data: DictData = []
    # 移除BOM头
    if content.startswith('\ufeff'):
        content = content[1:]
    if not content.strip():
        return []

    if format_key == "AiNiee_JSON":
        json_data = json.loads(content)
        for item in json_data:
            data.append({'org': item.get('src', ''), 'rep': item.get('dst', ''), 'note': item.get('info', '')})
    elif format_key == "GPPGUI_TOML":
        toml_data = toml.loads(content)
        for item in toml_data.get('gptDict', []):
            data.append({'org': item.get('org', ''), 'rep': item.get('rep', ''), 'note': item.get('note', '')})
    elif format_key == "GPPCLI_TOML":
        toml_data = toml.loads(content)
        for item in toml_data.get('gptDict', []):
            data.append({'org': item.get('searchStr', ''), 'rep': item.get('replaceStr', ''), 'note': item.get('note', '')})
    elif format_key == "GalTransl_TSV":
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith(('//', '#')):
                continue
            # 使用正则表达式分割，以处理制表符或四个空格
            parts = re.split(r'\t|(?<=\S) {4}(?=\S)', line, maxsplit=2)
            if len(parts) >= 2:
                entry = {
                    'org': parts[0].strip(),
                    'rep': parts[1].strip(),
                    'note': parts[2].strip() if len(parts) > 2 else ''
                }
                data.append(entry)
    else:
        raise ValueError(f"不支持的输入格式: {format_key}")
        
    return data

def format_output(data: DictData, format_key: str) -> str:
    """
    将标准的内部数据结构格式化为指定格式的文本字符串。

    Args:
        data: 包含字典条目的列表。
        format_key: 目标输出格式的键名。

    Returns:
        格式化后的文本字符串。
        
    Raises:
        ValueError: 如果目标格式键无效。
    """
    # TOML中单引号需要转义
    escape = lambda text: text.replace("'", "''")

    if format_key == "AiNiee_JSON":
        json_data = [{'src': item['org'], 'dst': item['rep'], 'info': item['note']} for item in data]
        return json.dumps(json_data, ensure_ascii=False, indent=2)
    
    elif format_key == "GPPGUI_TOML":
        lines = ["gptDict = ["]
        for item in data:
            lines.append(f"\t{{ org = '{escape(item['org'])}', rep = '{escape(item['rep'])}', note = '{escape(item['note'])}' }},")
        lines.append("]")
        return "\n".join(lines)
        
    elif format_key == "GPPCLI_TOML":
        entries = []
        for item in data:
            entry_str = (
                f"[[gptDict]]\n"
                f"note = '{escape(item['note'])}'\n"
                f"replaceStr = '{escape(item['rep'])}'\n"
                f"searchStr = '{escape(item['org'])}'"
            )
            entries.append(entry_str)
        return "\n\n".join(entries)
        
    elif format_key == "GalTransl_TSV":
        lines = []
        for item in data:
            line = f"{item['org']}\t{item['rep']}"
            if item['note']:
                line += f"\t{item['note']}"
            lines.append(line)
        return "\n".join(lines)
        
    else:
        raise ValueError(f"不支持的输出格式: {format_key}")

def reformat_content(content: str, format_display_name: str) -> str:
    """
    对给定内容进行重新格式化。它会先解析内容，然后再用相同的格式将其格式化输出。
    这可以用来清理和标准化文件格式。

    Args:
        content: 文件的文本内容。
        format_display_name: 内容的格式显示名称。

    Returns:
        重新格式化后的文本内容。
    """
    format_key = get_format_key(format_display_name, display_name=True)
    if not format_key:
        raise ValueError(f"无效的格式名称: {format_display_name}")

    # 解析和重新格式化的过程可以去除格式上的不一致（如多余的空格）
    # 并保留所有数据
    data = parse_input(content, format_key)
    return format_output(data, format_key)