# lumerical-fdtd-scripts
FDTD python脚本整理

## 使用说明
1. 通过`GUI.py`或者`non_GUI.py`配置`Lumerical`程序安装路径，要求：在该文件夹下应当存在对应版本号的文件夹，例如24R1版本应当存在`v241`。
2. 将程序生成的`config.json`和`lumapi.py`文件放到你的项目文件夹下。
3. 在代码开头导入即可使用。代码示例：
```python
import lumapi.LumAPI as lumapi

filename = 'a.fsp'
fdtd = lumapi.FDTD(filename)
```

