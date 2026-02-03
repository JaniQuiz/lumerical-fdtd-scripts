import json
import os
import importlib.util
import re
import platform
import sys
import shutil

# --- 核心修改：路径处理逻辑 ---
# 1. 确定基准路径 (处理 PyInstaller 打包后的临时目录)
if getattr(sys, 'frozen', False):
    # EXE模式：资源在临时目录 _MEIPASS
    BASE_DIR = sys._MEIPASS 
    # 导出目标：EXE 所在目录
    OUTPUT_DIR = os.path.dirname(sys.executable)
else:
    # 脚本模式：资源在当前脚本目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR = BASE_DIR

# 内部 lumapi 文件夹路径 (读取模板 lumapi.py 和写入 config.json 的地方)
LUMAPI_DIR = os.path.join(BASE_DIR, "lumapi")
CONFIG_PATH = os.path.join(LUMAPI_DIR, "config.json")

# 确保内部目录存在 (脚本模式下如果不存在则创建)
if not getattr(sys, 'frozen', False) and not os.path.exists(LUMAPI_DIR):
    os.makedirs(LUMAPI_DIR, exist_ok=True)
# ---------------------------

def get_lumapi_path(lumerical_root, version):
    """根据根路径和版本获取lumapi.py路径"""
    base_path = os.path.join(lumerical_root, version)
    # Ansys Unified
    ansys_path = os.path.join(base_path, "Lumerical", "api", "python", "lumapi.py")
    if os.path.exists(ansys_path):
        return ansys_path
    # Standalone
    standalone_path = os.path.join(base_path, "api", "python", "lumapi.py")
    if os.path.exists(standalone_path):
        return standalone_path
    return standalone_path

def detect_version(lumerical_root):
    """检测版本号"""
    try:
        if not os.path.exists(lumerical_root): return None
        for item in os.listdir(lumerical_root):
            item_path = os.path.join(lumerical_root, item)
            if os.path.isdir(item_path) and re.match(r'^v\d{3}$', item):
                if os.path.exists(get_lumapi_path(lumerical_root, item)):
                    return item
        return None
    except Exception: return None

def detect_common_paths():
    """自动扫描路径"""
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
            paths = [
                os.path.join(drive, "Program Files", "Lumerical"),
                os.path.join(drive, "Program Files (x86)", "Lumerical"),
                os.path.join(drive, "Lumerical"),
                os.path.join(drive, "Program Files", "Ansys Inc"),
                os.path.join(drive, "Program Files (x86)", "Ansys Inc")
            ]
            for p in paths:
                if os.path.exists(p):
                    v = detect_version(p)
                    if v: common_paths.append((p, v))
                    
    elif platform.system() == "Linux":
        paths = [
            "/opt/lumerical", "/usr/local/lumerical",
            "/usr/ansys_inc", "/opt/ansys_inc",
            os.path.expanduser("~/Ansys/ansys_inc"), os.path.expanduser("~/ansys_inc")
        ]
        for p in paths:
            if os.path.exists(p):
                v = detect_version(p)
                if v: common_paths.append((p, v))
                
    print(" 完成。")
    return common_paths

def validate_path(lumerical_root):
    """验证路径并加载环境"""
    try:
        if not lumerical_root: return "", ""
        lumerical_root = os.path.abspath(lumerical_root)
        version = detect_version(lumerical_root)
        if not version:
            print(f"错误：未找到有效版本 (在 {lumerical_root})")
            return "", ""
            
        lumapi_path = get_lumapi_path(lumerical_root, version)
        if not os.path.exists(lumapi_path):
            print(f"错误：API文件不存在")
            return "", ""
            
        # 测试加载
        spec = importlib.util.spec_from_file_location('lumapi', lumapi_path)
        lumapi = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lumapi)
        
        # Windows DLL 配置
        if platform.system() == "Windows":
            os.add_dll_directory(lumerical_root)
            bin_path = os.path.join(lumerical_root, version, "bin")
            if not os.path.exists(bin_path):
                bin_path = os.path.join(lumerical_root, version, "Lumerical", "bin")
            if os.path.exists(bin_path):
                os.add_dll_directory(bin_path)
        
        return lumapi_path, version
    except Exception as e:
        print(f"验证失败: {e}")
        return "", ""

def load_config():
    """读取配置"""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                return config.get('lumerical_path'), config.get('version')
    except: pass
    return None, None

def save_config(lumerical_path, version):
    """保存配置到内部目录"""
    try:
        # 脚本模式下需确保目录存在
        if not getattr(sys, 'frozen', False) and not os.path.exists(LUMAPI_DIR):
            os.makedirs(LUMAPI_DIR, exist_ok=True)

        with open(CONFIG_PATH, 'w') as f:
            json.dump({'lumerical_path': os.path.abspath(lumerical_path), 'version': version}, f, indent=4)
        print(f"\n[成功] 配置已保存至内部存储。")
        return True
    except Exception as e:
        print(f"[错误] 保存失败: {e}")
        return False

def export_files():
    """导出功能：将内部 lumapi.py 和 config.json 复制到 EXE 目录"""
    print(f"\n正在导出接口文件...")
    try:
        src_script = os.path.join(LUMAPI_DIR, "lumapi.py")
        src_config = CONFIG_PATH
        
        if not os.path.exists(src_script):
            print(f"[错误] 源文件丢失: {src_script}")
            print("请检查是否正确打包了 lumapi 文件夹。")
            return
        if not os.path.exists(src_config):
            print("[错误] 配置文件未找到，请先进行路径配置。")
            return

        dst_script = os.path.join(OUTPUT_DIR, "lumapi.py")
        dst_config = os.path.join(OUTPUT_DIR, "config.json")
        
        shutil.copy2(src_script, dst_script)
        shutil.copy2(src_config, dst_config)
        
        print(f"[成功] 文件已导出到: {OUTPUT_DIR}")
        print("  1. lumapi.py")
        print("  2. config.json")
    except Exception as e:
        print(f"[错误] 导出失败: {str(e)}")

def load_lumapi(lumerical_path, version):
    """加载模块并返回"""
    lumapi_path = get_lumapi_path(lumerical_path, version)
    spec = importlib.util.spec_from_file_location('lumapi', lumapi_path)
    lumapi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lumapi)
    print(f"\n成功加载 API: {lumapi_path}")
    return lumapi

def perform_configuration():
    """执行配置流程"""
    detected = detect_common_paths()
    if detected:
        print("\n检测到以下路径:")
        for i, (p, v) in enumerate(detected):
            t = "Ansys Unified" if "Ansys" in p or "ansys" in p else "Standalone"
            print(f"{i+1}. {p} (版本: {v}, {t})")
        print(f"{len(detected)+1}. 手动输入")
        print(f"{len(detected)+2}. 返回主菜单")
        
        try:
            sel = int(input("请选择: "))
            if 1 <= sel <= len(detected):
                path, ver = detected[sel-1]
                if validate_path(path)[0]:
                    save_config(path, ver)
                return
            elif sel == len(detected) + 2:
                return
        except ValueError: pass

    while True:
        path = input("\n请输入安装根目录 (输入 q 返回): ").strip()
        if path.lower() in ['q', 'quit']: return
        
        p_valid, v_valid = validate_path(path)
        if p_valid:
            save_config(path, v_valid)
            return

def main():
    print("=== Lumerical Python API 配置工具 (CLI) ===")
    print(f"工作目录: {OUTPUT_DIR}")
    
    while True:
        cfg_path, cfg_ver = load_config()
        has_config = (cfg_path is not None)
        
        print("\n-------------------------")
        if has_config:
            print(f"当前配置: {cfg_path} ({cfg_ver})")
            print("1. [启动] 加载此环境")
            print("2. [导出] 导出接口文件 (lumapi.py + config.json)")
            print("3. [重置] 重新配置路径")
            print("4. [退出] 退出程序")
        else:
            print("当前状态: 未配置")
            print("1. [配置] 开始配置新路径")
            print("2. [退出] 退出程序")
            
        choice = input("\n请输入选项: ").strip()
        
        if has_config:
            if choice == '1':
                # 加载环境并返回 API 对象 (如果是作为模块调用)
                # 同时也为了验证环境是否真正可用
                validate_path(cfg_path)
                return load_lumapi(cfg_path, cfg_ver)
            elif choice == '2':
                export_files()
                input("\n按回车键继续...")
            elif choice == '3':
                perform_configuration()
            elif choice == '4':
                sys.exit()
            else:
                print("无效选项")
        else:
            if choice == '1':
                perform_configuration()
            elif choice == '2':
                sys.exit()
            else:
                print("无效选项")

if __name__ == "__main__":
    main()