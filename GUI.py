import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
import json
import os
import platform
import importlib.util
import re
import sys
import shutil

class LumericalGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Lumerical路径配置")
        
        # --- 核心修改：路径处理 ---
        # 1. 确定基准路径 (处理 PyInstaller 打包后的临时目录)
        if getattr(sys, 'frozen', False):
            # EXE模式：资源在临时目录
            self.base_dir = sys._MEIPASS 
            # 导出目标：EXE所在目录
            self.output_dir = os.path.dirname(sys.executable)
        else:
            # 脚本模式：资源在当前脚本目录
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            self.output_dir = self.base_dir

        # 确保 lumapi 目录路径正确
        self.lumapi_dir = os.path.join(self.base_dir, "lumapi")
        self.config_path = os.path.join(self.lumapi_dir, "config.json")
        
        # 如果是脚本运行且目录不存在，创建它
        if not getattr(sys, 'frozen', False) and not os.path.exists(self.lumapi_dir):
            os.makedirs(self.lumapi_dir, exist_ok=True)
        # ------------------------

        # 初始化UI
        self.create_widgets()
        
        # 检查配置文件
        self.check_config()

    def create_widgets(self):
        # 路径输入框
        tk.Label(self.root, text="Lumerical/Ansys路径:").grid(row=0, column=0, padx=5, pady=5)
        self.path_var = tk.StringVar()
        self.path_combo = ttk.Combobox(self.root, textvariable=self.path_var, width=60, state="normal")
        self.path_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # 绑定事件
        self.path_combo.bind('<KeyRelease>', lambda e: self.validate_path(self.path_var.get()))
        self.path_combo.bind('<FocusOut>', lambda e: self.validate_path(self.path_var.get()))
        self.path_combo.bind("<<ComboboxSelected>>", self.on_path_selected)
        
        # 浏览按钮
        tk.Button(self.root, text="浏览...", command=self.browse_path).grid(
            row=0, column=2, padx=5, pady=5)
        
        # 状态显示
        self.status_label = tk.Label(self.root, text="等待输入...", fg="blue")
        self.status_label.grid(row=1, column=0, columnspan=3, padx=5, pady=5)
        
        # --- 按钮区域修改 ---
        # 使用 Frame 来并排显示按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=10)

        # 确认按钮
        self.confirm_btn = tk.Button(btn_frame, text="确认并保存配置", command=self.confirm_path)
        self.confirm_btn.pack(side=tk.LEFT, padx=10)

        # 导出按钮 (新增)
        self.export_btn = tk.Button(btn_frame, text="导出库文件", command=self.export_files, state=tk.DISABLED)
        self.export_btn.pack(side=tk.LEFT, padx=10)

    def detect_common_paths(self):
        """检测常见Lumerical及Ansys安装路径"""
        common_paths = []
        
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
                        version = self.detect_version(path)
                        if version: common_paths.append((path, version))
        
        elif platform.system() == "Linux":
            potential_paths = [
                "/opt/lumerical", "/usr/local/lumerical",
                "/usr/ansys_inc", "/opt/ansys_inc",
                os.path.expanduser("~/Ansys/ansys_inc"), os.path.expanduser("~/ansys_inc")
            ]
            for path in potential_paths:
                if os.path.exists(path):
                    version = self.detect_version(path)
                    if version: common_paths.append((path, version))
        
        return common_paths

    def detect_version(self, lumerical_root):
        """检测有效版本号"""
        try:
            if not os.path.exists(lumerical_root): return None
            for item in os.listdir(lumerical_root):
                item_path = os.path.join(lumerical_root, item)
                if os.path.isdir(item_path) and re.match(r'^v\d{3}$', item):
                    # 检查是否有 API 文件
                    if self.get_lumapi_path_internal_check(lumerical_root, item):
                        return item
            return None
        except Exception: return None

    def get_lumapi_path(self, lumerical_root, version):
        """获取路径 (用于UI显示和验证)"""
        base_path = os.path.join(lumerical_root, version)
        ansys_path = os.path.join(base_path, "Lumerical", "api", "python", "lumapi.py")
        if os.path.exists(ansys_path): return ansys_path
        standalone_path = os.path.join(base_path, "api", "python", "lumapi.py")
        if os.path.exists(standalone_path): return standalone_path
        return standalone_path

    def get_lumapi_path_internal_check(self, lumerical_root, version):
        """内部辅助函数：仅检查文件是否存在"""
        path = self.get_lumapi_path(lumerical_root, version)
        return os.path.exists(path)

    def check_config(self):
        """启动时检查配置"""
        valid_config = False
        config_path_val = None
        config_version = None
        
        common_paths = self.detect_common_paths()
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                lumerical_path = config.get('lumerical_path')
                version = config.get('version')
                
                if lumerical_path and version:
                    lumapi_path = self.get_lumapi_path(lumerical_path, version)
                    if os.path.exists(lumapi_path):
                        config_path_val = lumerical_path
                        config_version = version
                        valid_config = True
            except Exception: pass
        
        self.update_combobox(common_paths, config_path_val, config_version)
        
        if valid_config:
            self.path_var.set(config_path_val)
            self.validate_path(config_path_val)
            # 配置有效，启用导出按钮
            self.export_btn.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="请输入有效路径", fg="red")
            self.export_btn.config(state=tk.DISABLED)

    def update_combobox(self, paths, config_path=None, config_version=None):
        formatted_paths = []
        selected_index = 0
        for i, (path, version) in enumerate(paths):
            formatted_paths.append(f"{path} ({version})")
            if config_path and os.path.normpath(path) == os.path.normpath(config_path):
                selected_index = i
        
        self.path_combo['values'] = formatted_paths
        
        if config_path and config_version and not any(os.path.normpath(p[0]) == os.path.normpath(config_path) for p in paths):
            val = f"{config_path} ({config_version}) [配置文件]"
            self.path_combo['values'] = (val,) + self.path_combo['values']
            self.path_var.set(config_path)
        elif formatted_paths:
            self.path_combo.current(selected_index)
            self.path_var.set(formatted_paths[selected_index].split(" (")[0])

    def on_path_selected(self, event):
        selection = self.path_combo.get()
        if " (" in selection:
            path = selection.split(" (")[0]
            self.path_var.set(path)
            self.validate_path(path)

    def validate_path(self, path):
        try:
            if not path:
                self.status_label.config(text="请输入有效路径", fg="red")
                self.confirm_btn.config(state=tk.DISABLED)
                return False
                
            version = self.detect_version(path)
            if not version:
                self.status_label.config(text="未找到有效的版本文件夹(vXXX)", fg="red")
                self.confirm_btn.config(state=tk.DISABLED)
                return False
                
            lumapi_path = self.get_lumapi_path(path, version)
            if not os.path.exists(lumapi_path):
                 self.status_label.config(text=f"路径下未找到API文件", fg="red")
                 self.confirm_btn.config(state=tk.DISABLED)
                 return False

            spec = importlib.util.spec_from_file_location('lumapi', lumapi_path)
            lumapi = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(lumapi)
            
            is_ansys = "Ansys" in path or "ansys" in path or "Lumerical" in lumapi_path.replace(path, "")
            type_str = "Ansys Unified" if is_ansys else "Standalone"
            
            self.status_label.config(text=f"路径有效 ({version} - {type_str})", fg="green")
            self.confirm_btn.config(state=tk.NORMAL)
            return True
            
        except Exception as e:
            self.status_label.config(text=f"路径无效: {str(e)}", fg="red")
            self.confirm_btn.config(state=tk.DISABLED)
            return False

    def browse_path(self):
        path = filedialog.askdirectory(title="选择Lumerical或Ansys Inc安装目录")
        if path:
            self.path_var.set(path)
            self.validate_path(path)
            common = self.detect_common_paths()
            self.update_combobox(common, path, self.detect_version(path))

    def confirm_path(self):
        """确认并保存配置"""
        path = self.path_var.get()
        if not path: return
        version = self.detect_version(path)
        if not version:
            messagebox.showerror("错误", "未找到有效的版本号")
            return
            
        try:
            # 确保目录存在 (如果是脚本模式)
            if not getattr(sys, 'frozen', False):
                 os.makedirs(self.lumapi_dir, exist_ok=True)

            with open(self.config_path, 'w') as f:
                json.dump({
                    'lumerical_path': os.path.abspath(path),
                    'version': version
                }, f, indent=4)
            
            self.status_label.config(text=f"配置已保存 ({version})", fg="green")
            self.confirm_btn.config(state=tk.DISABLED) # 防止重复保存
            
            # --- 核心修改：保存成功后启用导出按钮 ---
            self.export_btn.config(state=tk.NORMAL, bg="#E0E0E0") 
            messagebox.showinfo("成功", f"配置已保存。\n您可以点击“导出”按钮提取文件。")
            
            common = self.detect_common_paths()
            self.update_combobox(common, path, version)
        except Exception as e:
            messagebox.showerror("错误", f"配置文件保存失败: {str(e)}")

    def export_files(self):
        """导出 config.json 和 lumapi.py 到 EXE 所在目录"""
        try:
            src_script = os.path.join(self.lumapi_dir, "lumapi.py")
            src_config = self.config_path # 已经在 check_config 或 confirm_path 中生成
            
            # 检查源文件
            if not os.path.exists(src_script):
                messagebox.showerror("错误", f"源文件丢失: {src_script}\n打包时请包含 lumapi 文件夹。")
                return
            if not os.path.exists(src_config):
                messagebox.showerror("错误", "配置文件未找到，请先点击'确认并保存'。")
                return

            dst_script = os.path.join(self.output_dir, "lumapi.py")
            dst_config = os.path.join(self.output_dir, "config.json")
            
            shutil.copy2(src_script, dst_script)
            shutil.copy2(src_config, dst_config)
            
            messagebox.showinfo("导出成功", 
                                f"文件已导出至:\n{self.output_dir}\n\n"
                                f"1. lumapi.py\n2. config.json\n\n"
                                "现在您可以直接复制这两个文件使用。")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = LumericalGUI(root)
    root.mainloop()