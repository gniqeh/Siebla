# Siebla

Windows 10/11 x64 离线 Python 办公工作台。无须在目标电脑安装 Python、pip 或联网。核心包含 Python 3.12.10、openpyxl 3.1.5 和 et_xmlfile 2.0.0。

## 核心构建

在联网 Windows x64 构建电脑：

```powershell
py build_windows.py --ui browser
# 可选：native、winforms、all
```

输出 `dist/Siebla-browser.zip` 等独立压缩包。每个核心 ZIP 不超过 **20,000,000 字节**。Python 官方嵌入式包放在 `runtime/python-3.12.10-embed-amd64.zip`。

Browser 版双击 `Siebla.exe` 或 `启动浏览器版.cmd`，启动本地网页及可关闭的命令行窗口。**关闭命令行窗口就结束服务**；仅关闭浏览器标签页不会结束服务。关闭命令行窗口前应确认保存状态。

Native 版无需浏览器；Windows Forms 版需要兼容的 .NET Framework。三个版本独立打包，不共享窗口源码。

## 浏览器版操作

- 单元格支持 **Shift+Enter** 运行当前格、**Tab** 缩进、上移、下移、清空输出及删除。
- **运行全部** 顺序执行；如有单元格报错则停止，避免后续步骤继续处理错误数据。
- 输入后自动保存至 `work/Siebla-notebook.json`；刷新网页自动恢复。顶部显示是否已保存，**Ctrl+S** 可手动保存到本地。
- **导出 JSON** 下载笔记本备份；**导入文件** 支持 Siebla JSON 和常规 IPYNB 中的代码单元格（不保留完整 Jupyter 富输出）。
- **加载 DLC** 通过 Windows 原生选择器任选一个 ZIP 分卷，自动扫描同文件夹内其他分卷。
- **已加载 DLC** 展示完整与不完整状态；**复制环境** 输出当前 Python 库及离线限制，便于粘贴给大模型。

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

`validate_dlcs.py` 会使用 Siebla 自带的 Python 实际检查三套单独安装及四种组合（共七种）的导入。**源码变更并不等于 Windows 实机测试成功**；请以本机输出为准。

## 注意事项

目标电脑完全离线；构建机首次下载 wheels 需要联网。Siebla 的 Python 嵌入式运行时、第三方 DLL、Office 文件兼容性以及单位软件白名单都应在目标 Win10 电脑上确认。第三方 DLC 和笔记本可包含可执行代码，不要导入不可信来源。
