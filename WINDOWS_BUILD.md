# Windows 打包说明

Windows `.exe` 需要在 Windows 环境打包。现在可以由 GitHub Actions 提供这个环境，无需先把源码压缩包传到自己的 Windows 电脑。

## GitHub 自动发布

公开仓库地址：`https://github.com/zsfan0628/GovPolicyWeekly`。

1. 在仓库 Actions 页面选择 `Windows Build and Release`，点击 Run workflow，可以生成测试包。
2. 在仓库的干净发布副本中推送版本标签（例如 `v1.0.0`），会自动构建并发布 Releases 下载文件。
3. 最终用户直接从 Releases 下载安装包或便携包，不需要安装构建依赖。

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub 构建使用 Python 3.12、官方 PyPI 和内置 Windows 环境，发布前检查真实 exe 的启动与报告导出。
为了控制体积，此发布版本不下载 Chromium，浏览器兜底使用目标电脑上的 Edge/Chrome；PDF 使用内置引擎。
构建测试文件只保留 3 天，正式安装包和便携包保存在 Releases。

本地开发目录有旧历史或私人配置时，先运行 `python scripts/prepare_github_source.py`。
它会生成 `.github-publish/GovPolicyWeekly` 干净发布目录并更新 Windows 源码 zip，不复制旧 `.git`、API Key 配置、输出报告或缓存。
首次上传应从这个干净目录创建新 Git 历史，不能直接推送原开发目录的旧历史。

## 1. 最简单方式

双击：

```text
build_windows.bat
```

脚本会尝试完成这些事：

1. 检测 Python；没有 Python 时优先下载 NuGet 版免安装 Python 3.10。
2. Windows 打包版使用 Qt/PySide6 UI，不再依赖 `tkinter`。
3. 创建 `.venv` 虚拟环境。
4. 使用清华 PyPI 镜像安装 Python 依赖、PyInstaller、Playwright、reportlab。
5. 尝试安装 Playwright Chromium，并打进 exe 目录；如果浏览器包下载失败，会改用 Windows 系统已安装的 Edge/Chrome 作为浏览器兜底。
6. 生成可执行文件目录。
7. 自动压缩出 `GovPolicyWeekly_windows_portable.zip`，这个 zip 可以传到其他 Windows 电脑解压运行。

注意：旧版 Tkinter UI 保留在 `app.py`，旧版 Qt Widgets UI 保留在 `qt_app.py`。当前 Windows 打包入口是 `desktop_app.py`，使用带真实采集功能的 Qt Quick 玻璃界面，需要 PySide6 6.10 或更新的 6.x 版本。新入口及 QML、壁纸、图标和着色器已加入打包配置，但本次 macOS 本地检查不等于 Windows 实机验收，发布前必须在 Windows 构建并执行 exe 自检。

生成后运行：

```text
dist\GovPolicyWeekly\GovPolicyWeekly.exe
```

请复制整个 `dist\GovPolicyWeekly` 文件夹，不要只复制单个 exe。

或者直接复制构建脚本生成的：

```text
GovPolicyWeekly_windows_portable.zip
```

在其他 Windows 电脑上解压后双击 `GovPolicyWeekly.exe`。

`GovPolicyWeekly_windows_portable.zip` 解压出来的内容，和 `dist\GovPolicyWeekly` 文件夹里的内容是同一套软件。区别只是 zip 更适合拷贝到其他电脑；运行时不要只拿单个 exe，要保留同目录下的 `_internal`、`config`、`input` 等文件夹。

## 2. PDF 生成

PDF 不再强制依赖 LibreOffice。

程序会先尝试：

1. 如果检测到 LibreOffice，就把 DOCX 转成 PDF。
2. 如果没有 LibreOffice，就使用内置 reportlab 引擎直接生成 PDF。

因此默认打包不需要安装 LibreOffice。

## 3. PowerShell 方式

在项目目录打开 PowerShell：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\build_windows.ps1
```

如果还要生成安装包：

```powershell
.\build_windows.ps1 -BuildInstaller
```

安装包输出目录：

```text
installer_output
```

安装包文件名类似：

```text
GovPolicyWeekly_Setup_1.0.0.exe
```

## 4. 可选：使用 LibreOffice 转 PDF

如果你特别想保留 DOCX 转 PDF 的排版方式，可以先手动安装 LibreOffice，然后运行：

```powershell
.\build_windows.ps1 -BundleLibreOffice
```

如果想让脚本尝试用 winget 安装 LibreOffice：

```powershell
.\build_windows.ps1 -BundleLibreOffice -AllowWingetLibreOffice
```

但默认不建议这样做，因为 winget 在部分网络环境下容易卡住。

## 5. 浏览器兜底

脚本会优先把 Playwright Chromium 放入 `dist\GovPolicyWeekly`。

如果 Playwright 浏览器包下载失败，软件仍会继续打包；运行时浏览器兜底会自动查找 Windows 系统里的 Microsoft Edge 或 Google Chrome。Windows 10/11 通常自带 Edge。

## 6. 体积说明

Windows 便携包的主要体积来自 PySide6 桌面界面、Playwright 浏览器驱动、python-docx、openpyxl、reportlab 等运行库。

当前打包配置已经做了基础瘦身：不再打入 pandas/numpy/tqdm，也不再收集完整 PySide6。新界面需要 QtCore、QtGui、QtWidgets、QtQml、QtQuick、QtQuickControls2 和 QtSvg 及其依赖，不应为了减小体积再排除这些运行库。构建结束时脚本会输出 size report，方便查看最大文件来源。
