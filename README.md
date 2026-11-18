# Siebla

Windows 10/11 x64 离线 Python 办公工作台。无须在目标电脑安装 Python、pip 或联网。核心包含 Python 3.12.10、openpyxl 3.1.5 和 et_xmlfile 2.0.0。

## Windows EXE 图标

构建时会自动使用仓库根目录的 `国家南方电网融合徽标 (1).png` 生成多尺寸 ICO，并写入三个版本的 `Siebla.exe` 图标资源。生成的临时 ICO 存放于 `downloads/siebla-icon.ico`，不单独放进最终便携 ZIP。构建电脑首次可能需要安装 Pillow 用于 PNG 转 ICO，目标电脑不需要它。图标会占用一定 ZIP 空间，浏览器版仍强制不超过18,000,000字节；Windows 构建与图标实际显示尚需验证。

## 核心构建

在联网 Windows x64 构建电脑：

```powershell
py build_windows.py --ui browser
# 可选：native、winforms、all
```

输出 `dist/Siebla-browser.zip` 等独立压缩包。浏览器版核心 ZIP 上限为 **18,000,000 字节**；Native 和 WinForms 仍为 **20,000,000 字节**。Python 官方嵌入式包放在 `runtime/python-3.12.10-embed-amd64.zip`。

Browser 版双击 `Siebla.exe` 或 `启动浏览器版.cmd`，启动本地网页及可关闭的命令行窗口。**关闭命令行窗口就结束服务**；仅关闭浏览器标签页不会结束服务。关闭命令行窗口前应确认保存状态。

Native 版无需浏览器；Windows Forms 版需要兼容的 .NET Framework。三个版本独立打包，不共享窗口源码。

## 浏览器版操作

- 单元格支持 **Shift+Enter** 运行当前格、自动显示代码行号、**Tab** 缩进或接受补全、上移、下移、清空输出及删除。
- **动态补全**：根据已运行的 Python 会话变量和对象成员，输入 `df.` 或 `pd.re` 后弹出候选；**Ctrl+空格** 手动触发，方向键选择，Tab/Enter 确认。补全只读取名称和静态属性，不执行用户代码，不能覆盖任意表达式或所有动态属性。
- **Jupyter 命令快捷键**：编辑代码时按 **Esc** 进入命令模式；此时 **A** 上插单元格、**B** 下插单元格、连续两次 **D** 删除当前单元格。按 **Enter** 返回编辑模式；在编辑模式输入 a/b/d 不触发快捷键。
- **运行全部** 顺序执行；如有单元格报错则停止，避免后续步骤继续处理错误数据。
- 输入后自动保存至 `work/Siebla-notebook.json`；刷新网页自动恢复。顶部显示是否已保存，**Ctrl+S** 可手动保存到本地。
- **导出 JSON** 下载笔记本备份；**导入文件** 支持 Siebla JSON 和常规 IPYNB 中的代码单元格（不保留完整 Jupyter 富输出）。
- **加载 DLC** 通过 Windows 原生选择器任选一个 ZIP 分卷，自动扫描同文件夹内其他分卷。
- **已加载 DLC** 展示完整与不完整状态；**复制环境** 输出当前 Python 库及离线限制，便于粘贴给大模型。
- **查看变量**：显示当前 Python 会话中的变量名称、类型和安全的简短预览；不执行对象的自定义 `repr`。
- **重启内核**：操作前需要确认，清空当前用户变量和补全上下文，但保留代码、已显示的输出、自动保存文件以及 DLC。这是**轻量会话重置**而非完整 Python 进程重启，已导入模块的内部状态和进程级设置可能保留。

本地工作目录为 `work/`；重要数据请额外备份。代码单元格直接执行 Python，打开第三方笔记本前先核实其来源。不是完整的 Jupyter。

## 三个 DLC 套件

| 名称 | 包含的主要功能 |
| --- | --- |
| **Siebla-Excel** | pandas、NumPy、openpyxl、XlsxWriter、RapidFuzz、pyxlsb 等，支持数据匹配、清洗、合并及 Excel 报表 |
| **Siebla-PDF** | pypdf、PyMuPDF、ReportLab、Pillow 等，支持 PDF 页面与文本处理及生成 |
| **Siebla-Media** | Pillow、piexif、ImageHash、NumPy、SciPy 等，支持图片转换、EXIF 和相似图检查 |

**Pandas 与 NumPy 已包含在 Siebla-Excel 中**，不再有独立的 PandasDLC。每个套件包含自己的必要依赖，可单独加载或任意组合；组合中重复安装的共用包仍需实机验证版本与 DLL 加载兼容性。

构建：

```powershell
py build_dlcs.py --dlc excel
py build_dlcs.py --dlc pdf
py build_dlcs.py --dlc media
py build_dlcs.py --dlc all
```

不带 `--dlc` 选项时，在交互式终端中显示四选一菜单，默认全部生成。打包器为 `dlc_packer.py`，不是旧的 Pandas 专用脚本。

每个 DLC 自动拆为 `Siebla-Excel_01.zip` 等分卷，**单卷不超过18,000,000字节**，尽量接近上限。将同一套件全部分卷放在同一目录，加载时选择任何一个即可自动识别其余分卷、逐块 SHA256 校验、一次性安装。缺卷时显示「不完整」，不安装半套包；完成后显示「正常」，该状态表示校验和安装成功，不保证实际 `import` 一定成功。

## 测试

```powershell
py -m unittest discover -s tests -v
py build_windows.py --ui browser
py build_dlcs.py --dlc all
py validate_dlcs.py
```

`validate_dlcs.py` 会使用 Siebla 自带的 Python 实际检查三套单独安装及四种组合（共七种）的导入。**浏览器版18,000,000字节限制和动态补全功能尚需 Windows 实机构建验证；源码变更并不等于 Windows 实机测试成功**；请以本机输出为准。

## 注意事项

目标电脑完全离线；构建机首次下载 wheels 需要联网。Siebla 的 Python 嵌入式运行时、第三方 DLL、Office 文件兼容性以及单位软件白名单都应在目标 Win10 电脑上确认。第三方 DLC 和笔记本可包含可执行代码，不要导入不可信来源。
