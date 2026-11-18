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

解压对应 ZIP，在解压目录中双击 `Siebla.exe`。可以写 Python 代码并执行单元格，单元格共享变量，显示文本输出和报错，使用内置 OpenPyXL 处理 XLSX。

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
- `native` 和 `browser` 不需要 C# 编译器。直接使用官方 `pythonw.exe` 的副本作为启动程序，利用 Python 自带启动模块打开选择的界面。
- `winforms` 构建机需要 `.NET Framework` 的 C# 编译器；目标电脑需要兼容的 .NET Framework，但不一定需要额外安装。
- Python 嵌入式版仍可能需要特定 Microsoft C Runtime 组件，是否完全免安装必须在干净的 Win10 x64 机器上验证。
- 目标电脑的单位软件白名单和未签名 EXE 提示依然可能阻止程序运行。
- 目前已完成源码提交，但尚未完成 Windows 实机端到端验证。GitHub Actions 如果受账号账单限制，也无法自动构建。

## GitHub Actions

在 Actions → Build Siebla → Run workflow 中选择 `native`、`winforms`、`browser` 或 `all`。但若 GitHub Actions 因账号问题不能启动，仍可使用本机命令构建。

仓库源码不包含任何单位的工作数据。不要把办公文件提交到公开仓库。
