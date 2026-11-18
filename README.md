# Siebla

**离线、便携、单元格式 Python 3.11 办公笔记本。**

这个仓库只负责构建 Windows x64 发行包，不提交 Python 解释器、依赖缓存或生成品。

## 一键生成

进入 GitHub 仓库的 **Actions → Build Siebla → Run workflow**。构建完成后下载名为 `Siebla-Windows-x64` 的 Artifact，解压可得到 `Siebla.zip`。

也可以在联网 Windows 64 位电脑运行：

```powershell
py build_windows.py
```

构建结果：`dist/Siebla.zip`。发行 ZIP 包含 Python 3.11.9 Embedded、openpyxl 3.1.5、et_xmlfile 2.0.0 和本地 Notebook 界面，构建脚本严格检查 **20,000,000 字节**上限，超限失败。

## 离线使用

把 `Siebla.zip` 带到目标 Windows 电脑，解压后双击 `启动笔记本.cmd`。浏览器会打开本地页面。用 **Shift+Enter** 运行单元格，变量在单元格间共享，输出显示于单元格下方。工作目录是 `work/`。

## 下载缓存

构建脚本允许将 `python-3.11.9-embed-amd64.zip` 手工下载到 `downloads/`，以后无需重复下载。库 wheel 缓存在 `downloads/wheels/`。此缓存不提交仓库。

## 限制

这是轻量 Notebook，不是完整 Jupyter 内核。显示文本输出和错误信息；支持导入代码单元格、保存 JSON。openpyxl 能读写 XLSX，但不能计算公式。仅在 `127.0.0.1` 运行；代码具有当前 Windows 用户的文件权限，请只执行可信代码，并遵守单位软件规定。

首次构建需要联网；**最终发行包运行不需要联网或系统 Python**。Windows 实机验收仍应检查安全策略和 DLL 兼容性。
