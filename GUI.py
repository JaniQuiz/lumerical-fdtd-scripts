import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
import importlib.util

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

    def get_lumapi_path(self, lumerical_root):
        """从Lumerical根路径获取lumapi.py路径"""
        return os.path.join(lumerical_root, "v241", "api", "python", "lumapi.py")

    def get_lumerical_root(self, lumapi_path):
        """从lumapi.py路径获取Lumerical根路径"""
        return os.path.dirname(os.path.dirname(os.path.dirname(lumapi_path)))

    def check_config(self):
        """检查配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                lumapi_path = config.get('lumapi_path')
                if lumapi_path and os.path.exists(lumapi_path):
                    # 从lumapi.py路径获取Lumerical根路径用于显示
                    lumerical_root = self.get_lumerical_root(lumapi_path)
                    self.path_var.set(lumerical_root)
                    if self.validate_path(lumerical_root):
                        self.status_label.config(text="当前路径有效", fg="green")
                        return
            except Exception as e:
                messagebox.showerror("错误", f"配置文件读取失败: {str(e)}")
        
        self.status_label.config(text="请输入有效路径", fg="red")

    def validate_path(self, path):
        """验证路径有效性"""
        try:
            if not path:  # 空值检查
                self.status_label.config(text="请输入有效路径", fg="red")
                self.confirm_btn.config(state=tk.DISABLED)
                return False
                
            # 获取lumapi.py的完整路径
            lumapi_path = self.get_lumapi_path(path)
            
            if not os.path.exists(lumapi_path):
                self.status_label.config(text="lumapi.py未找到", fg="red")
                self.confirm_btn.config(state=tk.DISABLED)
                return False
                
            # 测试导入
            spec = importlib.util.spec_from_file_location('lumapi', lumapi_path)
            lumapi = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(lumapi)
            
            self.status_label.config(text="路径有效", fg="green")
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
                self.status_label.config(text="路径有效", fg="green")
            else:
                self.status_label.config(text="路径无效，请检查", fg="red")

    def confirm_path(self):
        """确认路径处理"""
        path = self.path_var.get()
        if not path:
            messagebox.showwarning("警告", "请输入路径")
            return
            
        if not self.validate_path(path):
            messagebox.showerror("错误", "路径无效，请重新选择")
            return
            
        # 获取lumapi.py的完整路径用于保存
        lumapi_path = self.get_lumapi_path(path)
        
        # 保存配置
        try:
            with open(self.config_path, 'w') as f:
                json.dump({'lumapi_path': os.path.abspath(lumapi_path)}, f)
            
            self.status_label.config(text="路径已更新并有效", fg="green")
            self.confirm_btn.config(state=tk.DISABLED)
            messagebox.showinfo("成功", "路径已更新并验证有效")
        except Exception as e:
            messagebox.showerror("错误", f"配置文件保存失败: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = LumericalGUI(root)
    root.mainloop()