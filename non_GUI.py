import json
import os
import importlib.util
import re

# 配置文件路径
CONFIG_PATH = "config.json"
# 默认路径
DEFAULT_PATH = "D:\\Program Files\\Lumerical"

def detect_version(lumerical_root):
    """检测Lumerical安装目录下的有效版本号"""
    try:
        if not os.path.exists(lumerical_root):
            return None
            
        # 检查是否存在v+三位数字的文件夹
        for item in os.listdir(lumerical_root):
            if os.path.isdir(os.path.join(lumerical_root, item)):
                # 匹配v+三位数字的模式，例如v231, v242
                if re.match(r'^v\d{3}$', item):
                    # 验证该目录下是否存在lumapi.py
                    lumapi_path = os.path.join(lumerical_root, item, "api", "python", "lumapi.py")
                    if os.path.exists(lumapi_path):
                        return item
        return None
    except Exception:
        return None

def validate_path(lumerical_root: str) -> tuple:
    """验证Lumerical根目录并返回(lumapi_path, version)元组"""
    try:
        if not lumerical_root:
            print("错误：路径不能为空")
            return ("", "")
            
        lumerical_root = os.path.abspath(lumerical_root)
        
        # 检测版本号
        version = detect_version(lumerical_root)
        if not version:
            print(f"错误：在指定路径未找到有效的Lumerical版本 (查找路径：{lumerical_root})")
            return ("", "")
            
        lumapi_path = os.path.join(lumerical_root, version, "api", "python", "lumapi.py")
        
        if not os.path.exists(lumapi_path):
            print(f"错误：在指定路径未找到 lumapi.py 文件（查找路径：{lumapi_path}）")
            return ("", "")
            
        # 测试导入
        spec = importlib.util.spec_from_file_location('lumapi', lumapi_path)
        lumapi = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lumapi)
        
        # 测试通过后添加 DLL 目录
        os.add_dll_directory(lumerical_root)
        
        return (lumapi_path, version)  # 返回lumapi.py的完整路径和版本号
        
    except Exception as e:
        print(f"错误：路径验证失败 - {str(e)}")
        return ("", "")

def load_config():
    """加载配置文件"""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                lumerical_path = config.get('lumerical_path')
                version = config.get('version')
                if lumerical_path and version:
                    # 检查路径是否有效
                    lumapi_path = os.path.join(lumerical_path, version, "api", "python", "lumapi.py")
                    if os.path.exists(lumapi_path):
                        return (lumerical_path, version)
    except Exception as e:
        print(f"警告：配置文件加载失败 - {str(e)}")
    return (None, None)

def save_config(lumerical_path: str, version: str):
    """保存配置文件"""
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump({
                'lumerical_path': os.path.abspath(lumerical_path),
                'version': version
            }, f)
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
        lumerical_root = input("\n请输入 Lumerical 路径（输入 q 退出）: ").strip()
        
        if lumerical_root.lower() in ['q', 'quit']:
            print("操作已取消")
            exit()
            
        lumapi_path, version = validate_path(lumerical_root)
        if lumapi_path and version:
            if save_config(lumerical_root, version):
                return (lumerical_root, version)

def main():
    # 1. 尝试加载配置文件
    config_lumerical_path, config_version = load_config()
    if config_lumerical_path and config_version:
        # 验证配置文件路径有效性
        lumapi_path, version = validate_path(config_lumerical_path)
        print(f"\n使用配置文件中的路径：{config_lumerical_path} (版本: {config_version})")
        print(f"配置文件有效性：{'有效 ✔' if lumapi_path and version else '无效 ✘'}")
        
        if lumapi_path and version:
            choice = show_menu(True)
            if choice == 1:
                lumerical_path, version = get_user_input()
                return load_lumapi(lumerical_path, version)
            return load_lumapi(config_lumerical_path, config_version)
    
    # 2. 配置文件无效时使用默认路径尝试
    print(f"\n尝试默认路径：{DEFAULT_PATH}")
    lumapi_path, version = validate_path(DEFAULT_PATH)
    print(f"默认路径有效性：{'有效 ✔' if lumapi_path and version else '无效 ✘'}")
    
    if lumapi_path and version:
        choice = show_menu(True)
        if choice == 1:
            lumerical_path, version = get_user_input()
            return load_lumapi(lumerical_path, version)
        if save_config(DEFAULT_PATH, version):
            return load_lumapi(DEFAULT_PATH, version)
    
    # 3. 进入用户输入模式
    print("\n未找到有效配置，需要配置 Lumerical 路径")
    while True:
        choice = show_menu(False)
        if choice == 1:
            lumerical_path, version = get_user_input()
            if lumerical_path and version:
                return load_lumapi(lumerical_path, version)
        else:
            exit()

def load_lumapi(lumerical_path: str, version: str):
    """加载 lumapi 模块"""
    lumapi_path = os.path.join(lumerical_path, version, "api", "python", "lumapi.py")
    spec = importlib.util.spec_from_file_location('lumapi', lumapi_path)
    lumapi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lumapi)
    print(f"成功：lumapi 模块加载成功 (路径: {lumapi_path})")
    return lumapi

if __name__ == "__main__":
    lumapi = main()