# GovPolicyWeekly 政策周报

[English](README.md) | **简体中文**

采集中国政府网站的政策文件与人事任免信息，生成标题可点击跳转原文的 PDF 周报。

## 桌面工作台

- 玻璃质感导航、内置冰川背景与可关闭的启动动画。
- 下拉日历、带选中高亮的“近 7 天 / 近 30 天”快捷范围、30 个站点搜索多选。
- 真实采集进度、日志筛选、停止任务和历史报告。
- 获取并选择 OpenAI 兼容服务的模型，可选规则兜底。
- 附件下载与内置 PDF 生成，不强制安装 LibreOffice；同时保留 Word、Excel 和 JSON 导出。
- 自动保存本地配置，密钥遮挡显示，可减少动画和透明效果。

主工作台已连接真实采集引擎。`ui_preview.py` 单独保留为明确标注的离线外观演示。

## Windows 下载

前往 [GitHub Releases](https://github.com/zsfan0628/GovPolicyWeekly/releases/latest)：

- **安装版：**运行 `GovPolicyWeekly_Setup_*.exe`。
- **便携版：**完整解压 `GovPolicyWeekly_windows_portable.zip`，打开其中的 `GovPolicyWeekly.exe`，不要只复制单个 exe。

支持 Windows 10/11 64 位。已打包的软件无需另外安装 Python 或 LibreOffice。精简的 GitHub 构建使用电脑已安装的 Edge 或 Chrome 进行浏览器兜底。

**源码更新不会自动更新已下载的软件。** 已有 Release 可能仍使用旧界面，请查看对应的发布说明；新版工作台需要重新通过 Windows 构建后，才会出现在可下载的 exe 中。

## 源码运行

使用 Python 3.10 或更新版本；桌面界面要求 PySide6 6.10 或更新的 6.x 版本。

```bash
python -m venv .venv
# Windows：
.venv\Scripts\activate
# macOS / Linux：
source .venv/bin/activate
python -m pip install -r requirements-windows-build.txt
python desktop_app.py
```

macOS 可以创建可双击的桌面入口：

```bash
python scripts/create_mac_preview_app.py --production
```

该入口依赖当前项目目录与 Python 环境，并不是可单独分发的 macOS 安装包，请保留它们的位置。

旧界面保留在 `qt_app.py` 与 `app.py`（后者需要 Tkinter）。运行 `python ui_preview.py` 可打开离线外观演示。

## 生成周报

1. 选择日期与需要采集的站点；快捷范围截止到昨天。
2. 填写模型服务的 API 根地址与密钥，点击“获取模型”并选择模型。也可关闭大模型，仅使用已配置的规则。
3. 选择输出目录与运行选项，点击“开始生成”。
4. 从工作台或历史报告打开 PDF，结合警告与原文链接人工复核。

栏目与详情不设置数量上限，大范围任务可能耗时较长。程序遍历可发现的公开栏目与分页，不代表能找到每个网站的所有页面。浏览器兜底可辅助读取 JavaScript 页面及部分受限入口，但不保证所有站点均可访问。

明确命中的内容由规则保留，明确不属于目标的内容被排除；模糊候选交给所选模型复判。未启用模型时，模糊候选默认排除，除非显式开启规则兜底。

## 隐私与本地配置

使用者自行提供模型 API 凭证。模型请求会发送至你配置的服务，可能按服务商规则计费。

- 新工作台会遮挡显示 API Key，并在日志中隐藏已知密钥；**本地配置文件并未加密**。
- macOS 配置位于 `~/Library/Application Support/GovPolicyWeekly/`，Windows 位于 `%APPDATA%\GovPolicyWeekly\`，Linux 使用 XDG 配置目录。
- 首次启动可导入应用目录中的旧 `user_settings.json`，不会改写旧文件。
- 允许发布的源码包不包含个人配置、环境文件、报告、日志、缓存、虚拟环境及旧开发 Git 历史。
- 不要把个人配置、凭证、个人路径或生成报告发到公开 issue 或仓库；分享诊断信息前先脱敏。

维护者分发源码前应运行 `python scripts/prepare_github_source.py`。通过 `--upload-dir` 指定**全新、尚不存在的目标路径**可生成经过检查的浏览器上传快照。脚本会检测已知本地凭证、常见令牌格式和个人主目录路径，发现匹配后中止。该检查用于降低风险，不能保证识别任意私人信息。

## 命令行

```bash
python main.py --start-date 2026-10-01 --end-date 2026-10-07
```

在自己的环境中设置 `GOV_REPORT_OPENAI_BASE_URL`、`GOV_REPORT_OPENAI_API_KEY` 和 `GOV_REPORT_OPENAI_MODEL`，不要提交真实值。命令行也支持旧版应用目录配置；新工作台会把保存的配置直接传给独立采集进程。

常用参数包括 `--no-llm`、`--no-browser-fallback`、`--no-download-attachments` 和 `--allow-rule-fallback`，完整列表见 `python main.py --help`。

## 测试与构建

```bash
python -m unittest discover -s tests -v
python desktop_app.py --self-test release-check/desktop-self-test.json
python desktop_app.py --smoke-test --artifacts release-check/desktop-integration
python ui_preview.py --smoke-test
```

桌面集成检查使用本地 HTTP 网站和本地模型测试服务，运行真实采集进程、分类、附件下载、带链接的 PDF 导出、配置保存与停止流程，不调用付费 API 或真实政府网站。

GitHub Actions 可构建并检查 Windows exe、安装包和便携包。推送版本标签后通过检查才发布 Release，手动运行工作流可生成测试产物。详见 [Windows 构建说明](WINDOWS_BUILD.md)。

## 网站覆盖与素材

最近一次有记录的网站导航检查为 **2026-10-18**，覆盖 30 个站点的公开栏目、分页、按钮、下拉选项与检索入口，不代表验证所有历史页面、登录服务或表单提交。详见[逐站检查报告](docs/site-audit-2026-10-18.md)与[变更记录](CHANGELOG.md)。网站可能在测试后继续更新。

图标采用 Lucide，遵循 ISC 许可。壁纸来源与 Unsplash 许可见[素材说明](ui/preview/assets/ATTRIBUTION.md)。玻璃效果是跨平台 Qt 自定义实现，并非 Apple 原生 Liquid Glass API；动画参考见[界面说明](ui/preview/README.md)。
