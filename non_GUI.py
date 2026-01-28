import json
import os
from pathlib import Path
import importlib.util

# 配置文件路径
CONFIG_PATH = "config.json"
# 默认路径（修正拼写错误）
DEFAULT_PATH = "D:\\Program Files\\Lumerical"

def validate_path(path: str) -> bool:
    """验证路径有效性"""
    try:
        if not path:
            print("错误：路径不能为空")
            return False
            
        input_path = Path(path).resolve()
        lumapi_path = input_path / "v241" / "api" / "python" / "lumapi.py"
        
        if not lumapi_path.exists():
            print(f"错误：在指定路径未找到 lumapi.py 文件（查找路径：{lumapi_path}）")
            return False
            
        # 测试导入
        spec = importlib.util.spec_from_file_location('lumapi', str(lumapi_path))
        lumapi = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lumapi)
        
        # 测试通过后添加 DLL 目录
        os.add_dll_directory(str(input_path))
        
        return True
        
    except Exception as e:
        print(f"错误：路径验证失败 - {str(e)}")
        return False

def load_config():
    """加载配置文件"""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                path = config.get('lumerical_path')
                if path and os.path.exists(path):  # 检查路径是否存在
                    return path
    except Exception as e:
        print(f"警告：配置文件加载失败 - {str(e)}")
    return None

def save_config(path: str):
    """保存配置文件"""
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump({'lumerical_path': str(Path(path).resolve())}, f)
        return True
    except Exception as e:
        print(f"错误：配置文件保存失败 - {str(e)}")
        return False

def show_menu(valid: bool) -> int:
    """显示操作菜单"""
    print("\n请选择操作：")
    if valid:
        print("1. 修改 Lumerical 路径配置")
        print("2. 使用当前有效路径")
    else:
        print("1. 配置 Lumerical 路径")
        print("2. 退出程序")
    
    while True:
        try:
            choice = int(input("请输入选项 (1-2): "))
            if choice in [1, 2]:
                return choice
            print("错误：请输入有效选项 (1-2)")
        except ValueError:
            print("错误：请输入数字选项")

def get_user_input():
    """获取用户输入并处理"""
    while True:
        path = input("\n请输入 Lumerical 路径（输入 q 退出）: ").strip()
        
        if path.lower() in ['q', 'quit']:
            print("操作已取消")
            exit()
            
        if validate_path(path):
            if save_config(path):
                return path

def main():
    # 1. 尝试加载配置文件
    config_path = load_config()
    if config_path:
        # 验证配置文件路径有效性
        is_valid = validate_path(config_path)
        print(f"\n使用配置文件中的路径：{config_path}")
        print(f"配置文件有效性：{'有效 ✔' if is_valid else '无效 ✘'}")
        
        if is_valid:
            choice = show_menu(True)
            if choice == 1:
                return load_lumapi(get_user_input())
            return load_lumapi(config_path)
    
    # 2. 配置文件无效时使用默认路径尝试
    print(f"\n尝试默认路径：{DEFAULT_PATH}")
    is_valid_default = validate_path(DEFAULT_PATH)
    print(f"默认路径有效性：{'有效 ✔' if is_valid_default else '无效 ✘'}")
    
    if is_valid_default:
        choice = show_menu(True)
        if choice == 1:
            return load_lumapi(get_user_input())
        if save_config(DEFAULT_PATH):
            return load_lumapi(DEFAULT_PATH)
    
    # 3. 进入用户输入模式
    print("\n未找到有效配置，需要配置 Lumerical 路径")
    while True:
        choice = show_menu(False)
        if choice == 1:
            path = get_user_input()
            if validate_path(path):
                if save_config(path):
                    return load_lumapi(path)
        else:
            exit()

def load_lumapi(path: str):
    """加载 lumapi 模块"""
    lumapi_path = Path(path).resolve() / "v241" / "api" / "python" / "lumapi.py"
    
    spec = importlib.util.spec_from_file_location('lumapi', str(lumapi_path))
    lumapi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lumapi)
    print("成功：lumapi 模块加载成功")
    return lumapi

if __name__ == "__main__":
    lumapi = main()