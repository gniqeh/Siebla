# Siebla

**离线 Python 办公笔记本构建仓库**。只做一件事：把 Python 3.12.10、Excel 基础库和指定的窗口界面打包成可在 Windows 10 x64 上解压运行的 ZIP。

## 选择界面（三选一）

在**联网的 Windows 64位构建机**中：

```powershell
py build_windows.py --ui native
py build_windows.py --ui winforms
py build_windows.py --ui browser

# 一次分别构建三个版本（调试推荐）
py build_windows.py --ui all
```

不带 `--ui` 且在终端运行时，会出现 1/2/3/4 选择菜单，其中 **4 = all**；默认 `native`。`all` 会顺序生成三个独立 ZIP，某一版失败仍会尝试另外两版，最后汇总结果并以非零退出码报告失败。

| 参数 | 界面 | 运行电脑需要 |
| --- | --- | --- |
| `native` | Win32 原生窗口，代码单元格与输出区，无外部浏览器 | 不需要 .NET 或额外 GUI 框架 |
| `winforms` | Windows Forms 独立窗口，支持单元格列表、保存/打开 | 需要兼容的 .NET Framework（多数 Win10 有，但应检测） |
| `browser` | 本地服务及默认浏览器中的 Notebook | 需要兼容的浏览器 |

三种模式都自带 CPython **3.12.10**、`openpyxl==3.1.5`、`et_xmlfile==2.0.0`，最终各自打包，不把三套前端塞入同一个 ZIP。

构建结束后分别生成：

```text
dist/Siebla-native.zip
dist/Siebla-winforms.zip
dist/Siebla-browser.zip
```

默认每次构建只生成一个 ZIP；使用 `--ui all` 则一次分别生成三个 ZIP，严格检查每个单包不超过 **20,000,000 字节**。压缩包内有 `Siebla.exe`，目标电脑无需安装 Python，也无需操作 CMD。

## 核心使用

解压对应 ZIP，在解压目录中双击 `Siebla.exe`。浏览器版将显示一个命令行服务窗口，关闭它就会终止本地服务；也可以双击 `启动浏览器版.cmd` 启动浏览器版。仅关闭浏览器标签页不会退出服务。可以写 Python 代码并执行单元格，单元格共享变量，显示文本输出和报错，使用内置 OpenPyXL 处理 XLSX。

Native 原生版为了最小体积，使用“单元格列表 + 当前单元格编辑/输出”的布局，`Shift+Enter` 运行；通过“保存/打开”按钮使用固定文件 `work/Siebla-notebook.json`。

Windows Forms 版采用可滚动的多个单元格窗口，支持 `Shift+Enter` 和 JSON 文件对话框。Browser 版采用网页多单元格布局，浏览器保存 JSON 文件。笔记本格式统一为 `siebla-notebook-v1`。

**这不是完整 Jupyter**：没有 Jupyter kernel、科学计算全家桶、自动代码补全或富图表输出。

## 仓库运行时

官方 CPython 嵌入式 ZIP 已放在：

```text
runtime/python-3.12.10-embed-amd64.zip
```

构建直接读取此文件，不会从 Python 官网重复下载。OpenPyXL 的依赖 wheel 会缓存在 `downloads/wheels/`；首次构建若无缓存，构建机仍需联网。目标电脑运行时完全不需要联网。

## 构建与兼容限制

- 构建环境：Windows 64位、可运行的 Python 与 pip。
- `native` 和 `browser` 不需要 C# 编译器。Native 使用 `pythonw.exe` 启动无控制台窗口；Browser 使用 `python.exe` 启动并保留可关闭的服务控制台，关闭控制台即结束服务。
- `winforms` 构建机需要 `.NET Framework` 的 C# 编译器；目标电脑需要兼容的 .NET Framework，但不一定需要额外安装。
- Python 嵌入式版仍可能需要特定 Microsoft C Runtime 组件，是否完全免安装必须在干净的 Win10 x64 机器上验证。
- 目标电脑的单位软件白名单和未签名 EXE 提示依然可能阻止程序运行。
- 目前已完成源码提交，但尚未完成 Windows 实机端到端验证。GitHub Actions 如果受账号账单限制，也无法自动构建。

## GitHub Actions

在 Actions → Build Siebla → Run workflow 中选择 `native`、`winforms`、`browser` 或 `all`。但若 GitHub Actions 因账号问题不能启动，仍可使用本机命令构建。

仓库源码不包含任何单位的工作数据。不要把办公文件提交到公开仓库。


## Native 版启动诊断

如果双击 `Siebla.exe` 后没有窗口，先检查 `work/siebla-startup-error.txt`；新版本会同时弹出错误提示。用于开发阶段的直接检查：

```powershell
cd dist/Siebla-native
.\python.exe -c "import ui_native; print('Native module import OK')"
.\python.exe -c "import ui_native; ui_native.main()"
```

第二条会直接启动窗口，若启动失败可以在 PowerShell 看到 Python 异常。上述诊断只用于开发机，不要求目标电脑操作终端。

## DLC：选择 ZIP，直接加载

三个界面均增加 **「加载 DLC」** 按钮。选择一个专门为 Siebla 准备的 ZIP 后，软件会验证解压路径、离线安装到 `extensions/<压缩包文件名>/site-packages/` 并将它加入当前 Python 的模块搜索路径。目标电脑不需要联网或安装 pip。

ZIP 中应直接包含 Python 库目录，或者使用 `site-packages/` 作为顶层目录。例如：

```text
Siebla-Pandas.zip
├── pandas/
├── pandas.libs/
├── numpy/
├── numpy.libs/
├── dateutil/
├── pytz/
├── tzdata/
├── six.py
└── ...（相应依赖和元数据）
```

一个 ZIP 应包含本 DLC 的全部依赖；不设计子 DLC 安装页面。名称不能与已经安装的 DLC 重复。安装可信任的 ZIP 后即可尝试 `import pandas as pd`，如遇二进制模块已加载、DLL 冲突等情况，重启 Siebla 再测试。

在联网构建机生成 Windows 64位 Python 3.12 的 Pandas DLC：

```powershell
py build_pandas_dlc.py
```

输出 `dlc_dist/Siebla-01-NumPy.zip` 和 `dlc_dist/Siebla-02-Pandas.zip`。**每个 ZIP 都强制小于等于20,000,000字节**，Pandas 的其他依赖放在第二包。离线电脑上依次点击两次「加载 DLC」，先选 NumPy，再选 Pandas。无需分卷功能，也无需手动合并压缩包。不要将不可信的 ZIP 导入办公电脑；Python 扩展含可执行代码和 DLL。

目前已提交功能源码，但尚未完成 Windows 10 上三种界面逐一构建和实机安装测试。


## Browser 版退出方式

浏览器版启动后会同时打开 **本地网页** 和 **Siebla Browser 命令行窗口**。关闭该命令行窗口，即终止对应 Python 本地服务，解除对程序文件的占用。不要把关闭网页标签误认为退出服务。还可以运行 `启动浏览器版.cmd`，它同样使用前台 Python 服务进程。关闭窗口属于强制终止，退出前请先在网页里保存笔记本。


### Pandas DLC 单包超20 MB时

当前构建器不再把 NumPy 与 Pandas 合并成一个大 ZIP，而是自动拆成两个独立小包，并分别检查20 MB上限：

```powershell
py build_pandas_dlc.py
```

在 Siebla 中点「加载 DLC」两次，依次选择 `Siebla-01-NumPy.zip` 和 `Siebla-02-Pandas.zip`。导入完成后测试 `import numpy as np; import pandas as pd`，必要时重启 Siebla。这个机制保持「选择一个 ZIP → 导入」，不需要额外的层级菜单。构建脚本尚未在 Windows 实机跑通，最终容量和可导入性以实际构建结果为准。
