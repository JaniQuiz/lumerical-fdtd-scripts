import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
import json
import os, platform
import importlib.util
import re

class LumericalGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Lumerical路径配置")
        self.config_path = "config.json"
        
        # 初始化UI
        self.create_widgets()
        
        # 检查配置文件
        self.check_config()

    def create_widgets(self):
        # 路径输入框（现在是可编辑的下拉框）
        tk.Label(self.root, text="Lumerical/Ansys路径:").grid(row=0, column=0, padx=5, pady=5)
        self.path_var = tk.StringVar()
        # 创建可编辑的Combobox，state="normal"表示可编辑
        self.path_combo = ttk.Combobox(self.root, textvariable=self.path_var, width=60, state="normal")
        self.path_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # 绑定事件，当文本变化时验证
        self.path_combo.bind('<KeyRelease>', lambda e: self.validate_path(self.path_var.get()))
        self.path_combo.bind('<FocusOut>', lambda e: self.validate_path(self.path_var.get()))
        # 添加下拉选择事件绑定
        self.path_combo.bind("<<ComboboxSelected>>", self.on_path_selected)
        
        # 浏览按钮
        tk.Button(self.root, text="浏览...", command=self.browse_path).grid(
            row=0, column=2, padx=5, pady=5)
        
        # 状态显示
        self.status_label = tk.Label(self.root, text="等待输入...", fg="blue")
        self.status_label.grid(row=1, column=0, columnspan=3, padx=5, pady=5)
        
        # 确认按钮
        self.confirm_btn = tk.Button(self.root, text="确认路径", command=self.confirm_path)
        self.confirm_btn.grid(row=2, column=1, pady=10)

    def detect_common_paths(self):
        """检测常见Lumerical及Ansys安装路径"""
        common_paths = []
        
        # 检测Windows系统
        if platform.system() == "Windows":
            # 检测所有盘符
            import string
            from ctypes import windll
            
            # 获取所有可用驱动器
            drives = []
            bitmask = windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drives.append(letter + ":\\")
                bitmask >>= 1
                
            # 检测每个驱动器的常见路径
            for drive in drives:
                potential_paths = [
                    # 原生 Lumerical 路径
                    os.path.join(drive, "Program Files", "Lumerical"),
                    os.path.join(drive, "Program Files (x86)", "Lumerical"),
                    os.path.join(drive, "Lumerical"),
                    # Ansys Unified Installer 路径
                    os.path.join(drive, "Program Files", "Ansys Inc"),
                    os.path.join(drive, "Program Files (x86)", "Ansys Inc")
                ]
                
                for path in potential_paths:
                    if os.path.exists(path):
                        version = self.detect_version(path)
                        if version:
                            common_paths.append((path, version))
        
        # 检测Linux系统
        elif platform.system() == "Linux":
            potential_paths = [
                "/opt/lumerical",
                "/usr/local/lumerical",
                # Ansys Unified Installer Linux 路径
                "/usr/ansys_inc",
                "/opt/ansys_inc",
                # 支持用户目录下的Ansys安装 (e.g., ~/Ansys/ansys_inc)
                os.path.expanduser("~/Ansys/ansys_inc"),
                os.path.expanduser("~/ansys_inc")
            ]
            
            for path in potential_paths:
                if os.path.exists(path):
                    version = self.detect_version(path)
                    if version:
                        common_paths.append((path, version))
        
        return common_paths

    def detect_version(self, lumerical_root):
        """
        检测安装目录下的有效版本号
        兼容两种结构：
        1. Standalone: root/v241/api/python/lumapi.py
        2. Ansys Unified: root/v252/Lumerical/api/python/lumapi.py
        """
        try:
            if not os.path.exists(lumerical_root):
                return None
                
            # 检查是否存在v+三位数字的文件夹
            for item in os.listdir(lumerical_root):
                item_path = os.path.join(lumerical_root, item)
                if os.path.isdir(item_path):
                    # 匹配v+三位数字的模式，例如v231, v242, v252
                    if re.match(r'^v\d{3}$', item):
                        # 情况1：检查旧版结构 (Standalone)
                        path_standalone = os.path.join(item_path, "api", "python", "lumapi.py")
                        if os.path.exists(path_standalone):
                            return item
                            
                        # 情况2：检查Ansys Unified结构 (包含Lumerical子文件夹)
                        path_ansys = os.path.join(item_path, "Lumerical", "api", "python", "lumapi.py")
                        if os.path.exists(path_ansys):
                            return item
            return None
        except Exception:
            return None

    def get_lumapi_path(self, lumerical_root, version):
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
            
        # 默认返回Standalone路径（即使不存在），用于显示或后续报错
        return standalone_path

    def get_lumerical_info(self, lumapi_path):
        """
        从lumapi.py路径反向获取Lumerical根路径和版本
        兼容两种路径深度
        """
        parts = lumapi_path.split(os.sep)
        
        # 检查 Standalone 结构: .../v241/api/python/lumapi.py
        # 倒数第4个应该是 vXXX
        if len(parts) >= 4 and re.match(r'^v\d{3}$', parts[-4]):
            version = parts[-4]
            lumerical_root = os.sep.join(parts[:-4])
            return lumerical_root, version
            
        # 检查 Ansys Unified 结构: .../v252/Lumerical/api/python/lumapi.py
        # 倒数第5个应该是 vXXX
        if len(parts) >= 5 and re.match(r'^v\d{3}$', parts[-5]):
            version = parts[-5]
            lumerical_root = os.sep.join(parts[:-5])
            return lumerical_root, version
            
        return None, None

    def check_config(self):
        """检查配置文件并自动检测常见路径"""
        valid_config = False
        config_path = None
        config_version = None
        
        # 检测常见路径
        common_paths = self.detect_common_paths()
        
        # 检查配置文件是否存在且有效
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                lumerical_path = config.get('lumerical_path')
                version = config.get('version')
                
                if lumerical_path and version:
                    # 验证配置是否有效
                    lumapi_path = self.get_lumapi_path(lumerical_path, version)
                    if os.path.exists(lumapi_path):
                        config_path = lumerical_path
                        config_version = version
                        valid_config = True
            except Exception as e:
                pass
        
        # 更新下拉框
        self.update_combobox(common_paths, config_path, config_version)
        
        # 如果有有效配置，使用配置
        if valid_config:
            # 设置Combobox的值为配置的路径
            self.path_var.set(config_path)
            if self.validate_path(config_path):
                # 这里的status_label可能会被validate_path覆盖，所以不需要额外操作
                pass
            return
        
        # 如果没有有效配置，显示提示
        self.status_label.config(text="请输入有效路径", fg="red")

    def update_combobox(self, paths, config_path=None, config_version=None):
        """更新下拉框选项"""
        # 格式化路径列表
        formatted_paths = []
        selected_index = 0
        
        for i, (path, version) in enumerate(paths):
            display_text = f"{path} ({version})"
            formatted_paths.append(display_text)
            
            # 如果这个路径是配置文件中的路径，设置为默认选择
            if config_path and os.path.normpath(path) == os.path.normpath(config_path):
                selected_index = i
        
        # 更新下拉框选项
        self.path_combo['values'] = formatted_paths
        
        # 如果有配置且有效，但不在检测到的路径中，添加到选项
        if config_path and config_version and not any(os.path.normpath(p[0]) == os.path.normpath(config_path) for p in paths):
            display_text = f"{config_path} ({config_version}) [配置文件]"
            self.path_combo['values'] = (display_text,) + self.path_combo['values']
            # 只设置纯路径，不是带版本信息的字符串
            self.path_var.set(config_path)
        elif formatted_paths:
            # 设置默认选择
            self.path_combo.current(selected_index)
            # 只设置纯路径，不是带版本信息的字符串
            pure_path = formatted_paths[selected_index].split(" (")[0]
            self.path_var.set(pure_path)

    def on_path_selected(self, event):
        """当下拉框选择变化时，提取纯路径"""
        selection = self.path_combo.get()
        if " (" in selection:
            # 提取纯路径（去掉版本信息）
            path = selection.split(" (")[0]
            self.path_var.set(path)
            self.validate_path(path)

    def validate_path(self, path):
        """验证路径有效性并自动检测版本号"""
        try:
            if not path:  # 空值检查
                self.status_label.config(text="请输入有效路径", fg="red")
                self.confirm_btn.config(state=tk.DISABLED)
                return False
                
            # 检测版本号
            version = self.detect_version(path)
            if not version:
                self.status_label.config(text="未找到有效的版本文件夹(vXXX)", fg="red")
                self.confirm_btn.config(state=tk.DISABLED)
                return False
                
            # 获取lumapi.py的完整路径 (get_lumapi_path 现在会自动处理两种结构)
            lumapi_path = self.get_lumapi_path(path, version)
            
            if not os.path.exists(lumapi_path):
                 self.status_label.config(text=f"路径下未找到API文件: {lumapi_path}", fg="red")
                 self.confirm_btn.config(state=tk.DISABLED)
                 return False

            # 测试导入
            spec = importlib.util.spec_from_file_location('lumapi', lumapi_path)
            lumapi = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(lumapi)
            
            # 显示成功信息，区分是原生Lumerical还是Ansys Unified
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
        """浏览文件夹对话框"""
        path = filedialog.askdirectory(title="选择Lumerical或Ansys Inc安装目录")
        if path:
            # 设置Combobox的值为路径
            self.path_var.set(path)
            self.validate_path(path)
            
            # 更新下拉框选项
            common_paths = self.detect_common_paths()
            self.update_combobox(common_paths, path, self.detect_version(path))

    def confirm_path(self):
        """确认路径处理"""
        path = self.path_var.get()
        if not path:
            messagebox.showwarning("警告", "请输入路径")
            return
            
        # 验证路径并自动检测版本号
        version = self.detect_version(path)
        if not version:
            messagebox.showerror("错误", "未找到有效的版本号")
            return
            
        # 保存配置
        try:
            with open(self.config_path, 'w') as f:
                json.dump({
                    'lumerical_path': os.path.abspath(path),
                    'version': version
                }, f)
            
            self.status_label.config(text=f"配置已保存 ({version})", fg="green")
            self.confirm_btn.config(state=tk.DISABLED)
            messagebox.showinfo("成功", f"路径已更新并验证有效\n版本: {version}")
            
            # 更新下拉框
            common_paths = self.detect_common_paths()
            self.update_combobox(common_paths, path, version)
        except Exception as e:
            messagebox.showerror("错误", f"配置文件保存失败: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = LumericalGUI(root)
    root.mainloop()