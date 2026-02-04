# lumerical-fdtd-scripts
FDTD python脚本整理

## 使用说明  
### 配置程序  
1. **下载程序** 根据使用的系统以及架构，下载`releases`中发布的程序。  
2. **配置目录** 配置安装的lumerical的目录，程序会自动寻找lumerical的目录，你也可以手动输入或通过浏览功能选择目录。    
  * 目录说明：在你选择的配置目录下应该存在一个代表lumerical版本的文件夹，比如`v241`代表24R1版本。  
3. **保存配置** 当你选择目录完毕后，程序会自动检查有效性，在确认有效后，点击`保存配置`按钮来保存你的配置。
4. **导出和使用** 有下面两种导出方式，选择其中一种即可。

### 导出到本地
1. **导出到本地** 点击`导出到本地目录`按钮，程序会在当前目录下生成`lumapi.py`和`config.json`。
2. **使用** 将生成的`lumapi.py`和`config.json`复制到你的工作目录下，在你的python代码开头导入即可使用

### 导出到python解释器(推荐)
1. **配置python解释器目录** 选择你接下来要使用的python解释器的目录，程序会根据环境变量自动寻找解释器目录，你也可以手动输入或者通过浏览按钮手动选择python解释器。
2. **导出到python解释器** 点击`导出到python解释器`按钮，程序会将库文件复制到该python解释器的库目录中，你无需手动复制程序，只要使用该python解释器即可在任意位置使用。

## 调用示例
 * **使用原始FDTD函数**  
    打开`a.fsp`文件，添加power监视器，关闭程序。与FDTD自带脚本语言相比，在传递变量时，需要将空格替换成'_'，例如在`addrect`函数中传递`z min`时，实际应该传递的变量为`z_min`。传递字符串时则与原本语言一致。
    ```python
    import lumapi.LumAPI as lumapi

    um = 1e-6
    nm = 1e-9

    nx, ny = 100, 100
    S = 0.5*um
    material_base = 'Au (Gold) - CRC'

    filename = 'a.fsp'
    fdtd = lumapi.FDTD(filename)
    fdtd.addrect(
        name="base",
        x=0,
        y=0,
        x_span=nx*S,
        y_span=ny*S,
        z_min=-0.3*um,
        z_max=0,
        material=material_base,
    )
    fdtd.select('base')
    fdtd.set('z min',-0.5*um)
    fdtd.save()
    fdtd.close()
    ```

 * **使用封装函数**  
   调用库中封装的近场计算远场函数，说明：
   ```python
    def Kirchhoff(lamb, x_near, y_near, E_near, x_far, y_far, z_far, mode='numba'):
        '''
        lamb: 波长
        x_near, y_near: 近场位置数据，x_near和y_near应当是一维ndarry数组
        E_near: 近场的电场数据，E_near应当是二维ndarry数组
        x_far, y_far, z_far: 远场的位置数据，应当是一维数据或者数值
        mode: 计算模式
            'common'('c')，   : 普通循环计算模式，兼容所有平台，最稳定，但速度最慢
            'threaded'('t')   : 多线程计算模式，能够吃满CPU资源，测试仅windows下可用，需要joblib库
            'vectorized'('v') : 矢量化计算模式，计算小数据非常快，但大数据会容易爆内存(目前还没写好)
            'numba'('n')      : numba计算模式，计算速度非常快，兼容windows和linux，需要numba库，**推荐使用**

        return: 远场电场数据np.ndarray(len(x_far),len(y_far),len(z_far))
        '''
   ```
   
   示例：
    ```python
    from lumapi import Kirchhoff

    um = 1e-6
    nm = 1e-9

    lamb = 1*um  # 波长
    k = 2*np.pi/lamb # 波矢
    p = 700*nm   # 周期
    kx = 100     # x方向采样数
    ky = 100     # y方向采样数

    x_near = np.round(np.arange(-kx/2*p, (kx/2+1)*p, p), decimals=15)
    y_near = np.round(np.arange(-ky/2*p, (ky/2+1)*p, p), decimals=15)
    X, Y = np.meshgrid(x_near, y_near)

    # 初始相位
    A = 1
    focal = 20*um    # 焦距
    phi = np.zeros_like(X)
    rad = np.sqrt(X**2 + Y**2)
    mask = rad <= (kx-20)/2*p
    phi[mask] = -k/(2*f) * (X[mask]**2 + Y[mask]**2)

    # 光场函数
    E_near = A * np.exp(1j * phi)

    # 远场设置
    x_far = 0
    y_far = np.round(np.arange(-ky/2*p, (ky/2+1)*p, p), decimals=15)
    z_far = np.round(np.arange(0, 40*um, p), decimals=15)

    E_far = Kirchhoff(x_near, y_near, E_near, x_far, y_far, z_far, mode='numba') # mode也可以简单传入'n', 't

    plt.figure()
    plt.imshow(np.abs(E_far)**2, extent=[y_far.min(), y_far.max(), z_far.min(), z_far.max()])
    plt.show()
    ```


