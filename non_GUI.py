import json
import os
import importlib.util
import re
import platform
import sys

# --- 修改：配置路径 ---
# 获取当前脚本所在的绝对目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 指向 lumapi 子目录
LUMAPI_DIR = os.path.join(CURRENT_DIR, "lumapi")
# 配置文件路径
CONFIG_PATH = os.path.join(LUMAPI_DIR, "config.json")

# 确保目录存在
if not os.path.exists(LUMAPI_DIR):
    os.makedirs(LUMAPI_DIR, exist_ok=True)
# --------------------

def get_lumapi_path(lumerical_root, version):
    """
    根据根路径和版本获取lumapi.py路径
    自动判断是Standalone结构还是Ansys Unified结构
    """
    base_path = os.path.join(lumerical_root, version)
    
    # 优先检查 Ansys Unified 结构 (vXXX/Lumerical/api/...)
    ansys_path = os.path.join(base_path, "Lumerical", "api", "python", "lumapi.py")
    if os.path.exists(ansys_path):
        return ansys_path
        
    # 其次检查 Standalone 结构 (vXXX/api/...)
    standalone_path = os.path.join(base_path, "api", "python", "lumapi.py")
    if os.path.exists(standalone_path):
        return standalone_path
        
    # 默认返回Standalone路径（即使不存在），用于显示
    return standalone_path

def detect_version(lumerical_root):
    """检测安装目录下的有效版本号"""
    try:
        if not os.path.exists(lumerical_root):
            return None
            
        for item in os.listdir(lumerical_root):
            item_path = os.path.join(lumerical_root, item)
            if os.path.isdir(item_path):
                if re.match(r'^v\d{3}$', item):
                    # 使用 get_lumapi_path 逻辑检查文件是否存在
                    lumapi_path = get_lumapi_path(lumerical_root, item)
                    if os.path.exists(lumapi_path):
                        return item
        return None
    except Exception:
        return None

def detect_common_paths():
    """检测常见Lumerical及Ansys安装路径"""
    common_paths = []
    print("正在自动扫描常见安装路径...", end="", flush=True)
    
    if platform.system() == "Windows":
        import string
        from ctypes import windll
        drives = []
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1: drives.append(letter + ":\\")
            bitmask >>= 1
            
        for drive in drives:
            potential_paths = [
                os.path.join(drive, "Program Files", "Lumerical"),
                os.path.join(drive, "Program Files (x86)", "Lumerical"),
                os.path.join(drive, "Lumerical"),
                os.path.join(drive, "Program Files", "Ansys Inc"),
                os.path.join(drive, "Program Files (x86)", "Ansys Inc")
            ]
            for path in potential_paths:
                if os.path.exists(path):
                    version = detect_version(path)
                    if version: common_paths.append((path, version))
    
    elif platform.system() == "Linux":
        potential_paths = [
            "/opt/lumerical", "/usr/local/lumerical",
            "/usr/ansys_inc", "/opt/ansys_inc",
            os.path.expanduser("~/Ansys/ansys_inc"),
            os.path.expanduser("~/ansys_inc")
        ]
        for path in potential_paths:
            if os.path.exists(path):
                version = detect_version(path)
                if version: common_paths.append((path, version))
    
    print(" 完成。")
    return common_paths

def validate_path(lumerical_root: str) -> tuple:
    """验证Lumerical根目录并返回(lumapi_path, version)元组"""
    try:
        if not lumerical_root:
            print("错误：路径不能为空")
            return ("", "")
            
        lumerical_root = os.path.abspath(lumerical_root)
        version = detect_version(lumerical_root)
        if not version:
            print(f"错误：在指定路径未找到有效的Lumerical/Ansys版本 (查找路径：{lumerical_root})")
            return ("", "")
            
        lumapi_path = get_lumapi_path(lumerical_root, version)
        if not os.path.exists(lumapi_path):
            print(f"错误：在指定路径未找到 lumapi.py 文件（查找路径：{lumapi_path}）")
            return ("", "")
            
        spec = importlib.util.spec_from_file_location('lumapi', lumapi_path)
        lumapi = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lumapi)
        
        if platform.system() == "Windows":
            os.add_dll_directory(lumerical_root)
            bin_path = os.path.join(lumerical_root, version, "bin") # Standalone
            if not os.path.exists(bin_path):
                bin_path = os.path.join(lumerical_root, version, "Lumerical", "bin") # Ansys
            if os.path.exists(bin_path):
                os.add_dll_directory(bin_path)
        
        return (lumapi_path, version)
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
                    lumapi_path = get_lumapi_path(lumerical_path, version)
                    if os.path.exists(lumapi_path):
                        return (lumerical_path, version)
    except Exception as e:
        print(f"警告：配置文件加载失败 - {str(e)}")
    return (None, None)

def save_config(lumerical_path: str, version: str):
    """保存配置文件到 lumapi/config.json"""
    try:
        # 确保目录存在
        if not os.path.exists(LUMAPI_DIR):
            os.makedirs(LUMAPI_DIR, exist_ok=True)

        with open(CONFIG_PATH, 'w') as f:
            json.dump({
                'lumerical_path': os.path.abspath(lumerical_path),
                'version': version
            }, f, indent=4)
        print(f"配置已保存至: {CONFIG_PATH}")
        return True
    except Exception as e:
        print(f"错误：配置文件保存失败 - {str(e)}")
        return False

def select_from_detected(detected_paths):
    """从检测到的路径中选择"""
    print("\n检测到以下安装路径：")
    for i, (path, version) in enumerate(detected_paths):
        type_str = "Ansys Unified" if "Ansys" in path or "ansys" in path else "Standalone"
        print(f"{i + 1}. {path} (版本: {version}, 类型: {type_str})")
    print(f"{len(detected_paths) + 1}. 手动输入路径")
    print(f"{len(detected_paths) + 2}. 退出程序")

    while True:
        try:
            choice = int(input(f"请选择 (1-{len(detected_paths) + 2}): "))
            if 1 <= choice <= len(detected_paths):
                return detected_paths[choice - 1]
            elif choice == len(detected_paths) + 1:
                return None
            elif choice == len(detected_paths) + 2:
                sys.exit()
            else:
                print("无效选项，请重试。")
        except ValueError:
            print("请输入数字。")

def get_user_input():
    """获取用户输入并处理"""
    detected_paths = detect_common_paths()
    
    if detected_paths:
        result = select_from_detected(detected_paths)
        if result:
            selected_path, selected_version = result
            print(f"\n正在验证选择的路径: {selected_path}...")
            lumapi_path, version = validate_path(selected_path)
            if lumapi_path and version:
                if save_config(selected_path, version):
                    return (selected_path, version)
    else:
        print("未自动检测到常见安装路径。")

    while True:
        lumerical_root = input("\n请输入 Lumerical/Ansys 根目录路径（输入 q 退出）: ").strip()
        if lumerical_root.lower() in ['q', 'quit']:
            print("操作已取消")
            sys.exit()
            
        lumapi_path, version = validate_path(lumerical_root)
        if lumapi_path and version:
            if save_config(lumerical_root, version):
                return (lumerical_root, version)

def load_lumapi(lumerical_path: str, version: str):
    """加载 lumapi 模块"""
    lumapi_path = get_lumapi_path(lumerical_path, version)
    spec = importlib.util.spec_from_file_location('lumapi', lumapi_path)
    lumapi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lumapi)
    print(f"成功：lumapi 模块加载成功")
    print(f"  - API路径: {lumapi_path}")
    print(f"  - 版本: {version}")
    return lumapi

def main():
    print("=== Lumerical Python API 配置工具 ===")
    
    config_lumerical_path, config_version = load_config()
    
    if config_lumerical_path and config_version:
        lumapi_path = get_lumapi_path(config_lumerical_path, config_version)
        print(f"\n当前配置：{config_lumerical_path} (版本: {config_version})")
        
        if os.path.exists(lumapi_path):
            print("配置状态：有效")
            print("\n1. 使用当前配置启动")
            print("2. 重新配置路径")
            print("3. 退出")
            
            while True:
                choice = input("请输入选项 (1-3): ").strip()
                if choice == '1':
                    validate_path(config_lumerical_path) 
                    return load_lumapi(config_lumerical_path, config_version)
                elif choice == '2':
                    break 
                elif choice == '3':
                    sys.exit()
        else:
            print("配置状态：无效 (文件不存在)")
    
    print("\n--- 开始配置新路径 ---")
    lumerical_path, version = get_user_input()
    return load_lumapi(lumerical_path, version)

if __name__ == "__main__":
    lumapi = main()