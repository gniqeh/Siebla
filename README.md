# Siebla

**Windows 64位、Python 3.11、离线便携式单元格笔记本。**

这个仓库的工作只有一件事：把本仓库源码和自带 Python 运行时打包成 **`dist/Siebla.zip`**，解压后可在无网络、未安装 Python 的 Windows 电脑上运行。

## 仓库结构

```text
Siebla/
├── runtime/
│   └── python-3.11.9-embed-amd64.zip    # 须提交的官方 Python 运行时（原 ZIP）
├── build_windows.py
├── notebook.py
├── index.html
├── app.js
├── style.css
├── 启动笔记本.cmd
└── .github/workflows/build.yml
```

**注意：目前仓库中的 `runtime/` 仅有说明文件，Python 二进制 ZIP 尚未上传。** 构建脚本会优先读取 `runtime/python-3.11.9-embed-amd64.zip`，不再自动从 Python 官网下载；为完整的离线源码构建，须将该 ZIP 提交到仓库。可以在开发机上用：

```powershell
mkdir runtime -Force
Copy-Item "你下载好的python-3.11.9-embed-amd64.zip" "runtime/python-3.11.9-embed-amd64.zip"
git add runtime/python-3.11.9-embed-amd64.zip
git commit -m "Vendor Python 3.11.9 embedded runtime"
git push
```

官方下载源：<https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip>

仓库中不应提交打包后的 `dist/`。如果临时不提交运行时，也可以将该 ZIP 放入本地 `downloads/` 作为备用缓存。

## 构建

在 Windows 64位电脑上，安装有 Python 和 pip 的构建环境中运行：

```powershell
py build_windows.py
```

或者在 GitHub Actions 里运行 **Build Siebla**。依赖版本锁定为 `openpyxl==3.1.5`、`et_xmlfile==2.0.0`，目前 wheel 仍需首次下载并缓存在 `downloads/wheels/`，**所以仅将 Python 放进源码，还不等于完全离线构建**。发布给用户的 `Siebla.zip` 则无需联网。

构建产物：`dist/Siebla.zip`。构建脚本强制压缩包不超过 **20,000,000 字节**。

## 使用

解压 `Siebla.zip`，双击 `启动笔记本.cmd`。浏览器打开本地 Notebook 界面。按 **Shift+Enter** 执行当前单元格，共享变量并立即展示文本结果。工作目录为 `work/`。

这个工具并非完整 Jupyter。它支持文本结果、异常和基础 XLSX 操作，不提供完整 Jupyter 内核、Excel 公式计算引擎或富交互输出。只执行可信任的代码。
