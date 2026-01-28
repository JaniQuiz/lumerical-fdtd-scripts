import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
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
        # 路径输入框
        tk.Label(self.root, text="Lumerical路径:").grid(row=0, column=0, padx=5, pady=5)
        self.path_var = tk.StringVar()
        self.path_entry = tk.Entry(self.root, textvariable=self.path_var, width=50)
        self.path_entry.grid(row=0, column=1, padx=5, pady=5)
        
        self.path_entry.bind('<KeyRelease>', lambda e: self.validate_path(self.path_var.get()))
        self.path_entry.bind('<FocusOut>', lambda e: self.validate_path(self.path_var.get()))
        
        # 浏览按钮
        tk.Button(self.root, text="浏览...", command=self.browse_path).grid(
            row=0, column=2, padx=5, pady=5)
        
        # 状态显示
        self.status_label = tk.Label(self.root, text="等待输入...", fg="blue")
        self.status_label.grid(row=1, column=0, columnspan=3, padx=5, pady=5)
        
        # 确认按钮
        self.confirm_btn = tk.Button(self.root, text="确认路径", command=self.confirm_path)
        self.confirm_btn.grid(row=2, column=1, pady=10)

    def detect_version(self, lumerical_root):
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

    def get_lumapi_path(self, lumerical_root, version):
        """从Lumerical根路径和版本获取lumapi.py路径"""
        return os.path.join(lumerical_root, version, "api", "python", "lumapi.py")

    def get_lumerical_info(self, lumapi_path):
        """从lumapi.py路径获取Lumerical根路径和版本"""
        # 例如：D:\Program Files\Lumerical\v241\api\python\lumapi.py
        # 返回：D:\Program Files\Lumerical, v241
        parts = lumapi_path.split(os.sep)
        if len(parts) >= 4 and parts[-4].startswith('v') and re.match(r'^v\d{3}$', parts[-4]):
            version = parts[-4]
            lumerical_root = os.sep.join(parts[:-4])
            return lumerical_root, version
        return None, None

    def check_config(self):
        """检查配置文件"""
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
                        self.path_var.set(lumerical_path)
                        if self.validate_path(lumerical_path):
                            self.status_label.config(text=f"当前路径有效 ({version})", fg="green")
                            return
            except Exception as e:
                messagebox.showerror("错误", f"配置文件读取失败: {str(e)}")
        
        self.status_label.config(text="请输入有效路径", fg="red")

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
                self.status_label.config(text="未找到有效的Lumerical版本", fg="red")
                self.confirm_btn.config(state=tk.DISABLED)
                return False
                
            # 获取lumapi.py的完整路径
            lumapi_path = self.get_lumapi_path(path, version)
            
            # 测试导入
            spec = importlib.util.spec_from_file_location('lumapi', lumapi_path)
            lumapi = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(lumapi)
            
            self.status_label.config(text=f"路径有效 ({version})", fg="green")
            self.confirm_btn.config(state=tk.NORMAL)
            return True
            
        except Exception as e:
            self.status_label.config(text=f"路径无效: {str(e)}", fg="red")
            self.confirm_btn.config(state=tk.DISABLED)
            return False

    def browse_path(self):
        """浏览文件夹对话框"""
        path = filedialog.askdirectory(title="选择Lumerical安装目录")
        if path:
            self.path_var.set(path)
            if self.validate_path(path):
                self.status_label.config(text=f"路径有效 ({self.detect_version(path)})", fg="green")
            else:
                self.status_label.config(text="路径无效，请检查", fg="red")

    def confirm_path(self):
        """确认路径处理"""
        path = self.path_var.get()
        if not path:
            messagebox.showwarning("警告", "请输入路径")
            return
            
        # 验证路径并自动检测版本号
        version = self.detect_version(path)
        if not version:
            messagebox.showerror("错误", "未找到有效的Lumerical版本")
            return
            
        # 保存配置
        try:
            with open(self.config_path, 'w') as f:
                json.dump({
                    'lumerical_path': os.path.abspath(path),
                    'version': version
                }, f)
            
            self.status_label.config(text=f"路径已更新并有效 ({version})", fg="green")
            self.confirm_btn.config(state=tk.DISABLED)
            messagebox.showinfo("成功", f"路径已更新并验证有效 ({version})")
        except Exception as e:
            messagebox.showerror("错误", f"配置文件保存失败: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = LumericalGUI(root)
    root.mainloop()