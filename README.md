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

## 通用 DLC v2：一个逻辑 DLC，多个 ZIP 分卷

Siebla 的 DLC 是**一个通用列表**，与具体库无关。比如 Pandas 和 NumPy 共同构成一个 `PandasDLC`，可能因为20 MB限制拆成几个 ZIP：

```text
PandasDLC/
├── PandasDLC_01.zip
├── PandasDLC_02.zip
├── PandasDLC_03.zip
└── PandasDLC_04.zip
```

在上述文件夹里，**只需在 Siebla 选择任意一个 ZIP**，程序会扫描它所在的文件夹，自动找齐其余分卷，验证各分卷与文件 SHA256 后一次性安装。

已加载 DLC 列表按**逻辑名称**显示，而不是按 NumPy、Pandas 或 ZIP 文件显示：

```text
目前加载的 DLC：
  PandasDLC （正常）
  WordDLC   （不完整）
```

- **正常**：全部分卷完整，数据校验通过并已安装到 `extensions/PandasDLC/`。这不等于模块实际 import 已经经过验证。
- **不完整**：缺少分卷，不会安装半套 Python 库，窗口会显示具体缺失的 ZIP 文件名。将分卷补齐放到同一个目录后再任选一个加载即可。
- 系统重启后自动激活已完整安装的 DLC，不需要反复导入。
- DLC 由 Siebla 自带的 Python 使用，目标机无需互联网、pip 或单独安装 Python。

浏览器版使用由本地 Siebla 进程打开的 **Windows 原生文件选择框**，因此也可以从所选 ZIP 的实际目录自动发现同文件夹的分卷。Native 与 Windows Forms 也使用本地文件选择框。

### 打包 PandasDLC

在能联网、有 Python 和 pip 的构建机执行：

```powershell
git pull
py build_pandas_dlc.py
```

脚本下载针对 Windows x64 / Python 3.12 的 Pandas、NumPy 和其他依赖，制作一个 `PandasDLC`，自动拆成 `PandasDLC_01.zip`、`PandasDLC_02.zip` 等。**每个 ZIP 独立不超过20,000,000字节**；分卷数量由实际依赖大小决定，不能预先假定只有两个。把 `dlc_dist/` 中这些同名前缀的分卷全部放在一起交付即可。

这是 Siebla 自定义的多卷 DLC ZIP 格式，**不是传统 ZIP 分卷**；不要用常规分卷压缩软件生成 `_01.zip` 文件后期待它被自动识别。必须由对应打包器生成带 `siebla-dlc.json` 清单的格式。

出于安全考虑，只导入可信来源的 DLC：扩展包能提供可执行 Python 代码和 Windows DLL。当前源码已提交，但 Windows 三界面与实际 Pandas DLL 导入尚待实机验收。


## 第一批独立 DLC 套件

DLC 生成器只有一个入口，构建时可选 **一个套件** 或 **全部三个**：

\`\`\`powershell
py build_dlcs.py --dlc excel
py build_dlcs.py --dlc pdf
py build_dlcs.py --dlc media
py build_dlcs.py --dlc all
\`\`\`

在终端直接执行 \`py build_dlcs.py\` 时，还可以选择 1/2/3/4，默认 4（全部）。

| DLC 名称 | 独立包含的核心依赖 | 使用场景 |
| --- | --- | --- |
| \`Siebla-Excel\` | pandas、NumPy、openpyxl、XlsxWriter、rapidfuzz、pyxlsb 及它们的依赖 | Excel 合并、跨表匹配、模糊匹配、数据清洗、报表 |
| \`Siebla-PDF\` | pypdf、PyMuPDF、reportlab 及其依赖 | PDF 拆分合并、内容提取、水印、报告生成 |
| \`Siebla-Media\` | Pillow、piexif、ImageHash 及其依赖（含 NumPy、SciPy、PyWavelets 等） | 图片批处理、EXIF、近似图片识别 |

三个 DLC **互不要求预先安装其他 DLC**。构建命令会下载面向 Windows x64 / Python 3.12 的全部所需 wheels，并打包进所选套件。共用的 NumPy 和 Pillow 指定了相同版本，以降低组合加载时的冲突风险。Siebla Core 本身仍自带 OpenPyXL。

输出目录示例：

\`\`\`text
dlc_dist/
├── Siebla-Excel/
│   ├── Siebla-Excel_01.zip
│   └── Siebla-Excel_02.zip
├── Siebla-PDF/
│   ├── Siebla-PDF_01.zip
│   └── ...
└── Siebla-Media/
    ├── Siebla-Media_01.zip
    └── ...
\`\`\`

每个 ZIP 的硬上限是 **20,000,000 字节**。每个 DLC 的分卷数量由实际文件体积决定。**每个套件的所有分卷必须放在同一文件夹**；选中任意一个分卷即可自动查找、校验并导入同一套件的其余分卷。不同套件则按需分别加载，各自独立记录「正常 / 不完整」状态。

构建机可能需要联网并安装 pip；**目标电脑始终不需要联网、额外安装 Python 或 pip**。目前仅提交了源码，三个套件所有组合的 Windows 实机导入和二进制 DLL 兼容性仍需要验证。


### 独立性与任意组合验证（构建机上执行）

```powershell
py build_windows.py --ui browser
py build_dlcs.py --dlc all
py validate_dlcs.py
```

`validate_dlcs.py` 会使用 **Siebla 自带的 Python 3.12** 在临时目录逐个测试 7 种安装组合：仅 Excel、仅 PDF、仅 Media、Excel+PDF、Excel+Media、PDF+Media，以及全部安装。每次从一个 DLC 的**最后一个分卷**发起安装，检查安装状态和套件内模块的实际 `import`，任意组合失败则返回非零退出码。此测试在 Windows 构建机执行，生成的 DLC ZIP 本身不包含测试环境。

旧命令 `py build_pandas_dlc.py` 现在相当于构建 `Siebla-Excel`。推荐统一使用 `py build_dlcs.py --dlc ...`。
