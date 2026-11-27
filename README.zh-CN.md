# GovPolicyWeekly 政策周报

[English](README.md) | **简体中文**

采集中国政府网站的政策文件与人事任免信息，生成标题可点击跳转原文的 PDF 周报。

## 桌面工作台

栏目来源、覆盖状态、日期证据、附件候选、重新核验与补采记录详见[采集质量说明](docs/retrieval-quality.md)。

PDF 概述新增异常提示，可跳转文末的访问异常明细；页面标题和完整地址均可点击。
非正文附件单独计为正常跳过，不再与网站请求失败混算。
DeepSeek 可填写 `https://api.deepseek.com` 和自己的 API Key，获取模型后下拉选择，
再使用“测试实际调用”验证生成能力（需确认，会消耗 API 用量）。

站点管理中的“配置已载入”仅表示站点配置已读取，不代表实时连通状态。

本地新版启动后在后台检查更新，有新版时才显示下载图标。也可在“站点管理”或“设置”
点刷新图标手动检查。新增站点、栏目和地图代表点可以单独更新；程序更新才下载对应的
完整安装包或便携包，且需要确认。没有更新功能的旧版仍需手动升级一次。
详见[更新机制与故障处理](docs/software-updates.md)。

运行 `python desktop_app.py`，或在 macOS 双击项目内的 `WorkspacePreview.command`，打开正式工作台。启动不会自动采集。

- 珍珠灰底色搭配雾玫瑰选中态。月历高亮所选日期并显示含首尾的总天数，跨月可翻页；点击「最近一期」的日期即可打开对应的本地周报。
- 任务动态按站点汇总进展、收录和待核查项；原始日志可在「技术明细」中筛选查看。
- 静音开场约 4.8 秒：一个光点投射出粒子，粒子落进笔画，形成「Welcome to Policy Weekly」。字母散成旋涡，再聚成「政策周报」回到左上角。片头可跳过；启用「减少动态效果」则直接进入。地图仍可在站点管理中使用。
- 下拉日历、带选中高亮的“近 7 天 / 近 30 天”快捷范围、30 个站点搜索多选。
- 真实采集进度、日志筛选、停止任务和历史报告。
- 获取并选择 OpenAI 兼容服务的模型，可选规则兜底。
- 测试实际模型调用、逐站采集覆盖明细、断点恢复和仅重试失败模型判断。

最新本地源码新增了[任务覆盖与恢复](docs/task-recovery.md)。此前发布的 Windows 安装包
不会自动获得这些功能，需要重新构建发布。
- 附件下载与内置 PDF 生成，不强制安装 LibreOffice；同时保留 Word、Excel 和 JSON 导出。
- PDF 统一采用紧凑版式：内嵌思源黑体简体中文，分类清单、浅色详情标题带、浅灰摘要区、页内跳转及采集判定附录。详见[PDF 版式说明](docs/pdf-layout.md)。
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

日常采集改为政策与人事核心栏目：当前从 30 个站点的 703 个预设入口中选用 410 个。读完一页就筛日期、处理文章；在日期连续倒序、完整可识别时保守停止历史翻页，最多同时处理三个不同站点，不给文章数量设上限。日期缺失或排序混乱时不按日期提前停止；覆盖率仍取决于可发现的公开页面和站点可访问性。

**每次启动软件时，“下载附件”默认关闭。** 报告仍保留附件原始链接；手动开启后先生成 PDF，再下载附件，不必等待附件下载完才能打开 PDF。正文和模型判断缓存跨日期范围复用，近期文章重新抓取，较旧文章的快照最多复用七天。完整遍历、禁用缓存及具体取舍见[采集性能与核对说明](docs/crawl-performance.md)。

明确命中的内容由规则保留；类别不明确时可交给所选模型复判。日期有争议且有本期线索时，可用同一模型核对标题和日期引文；无法验证原文则保留待核查。没有启用模型时，内容分类仍可显式开启规则兜底，但不会放宽日期要求。期前弱线索另存 `historical_date_hints.json`，不与 404 混排。

日期复核默认不限次数。在“模型复判”中勾选“限制日期复核请求”可设置整次任务的上限（CLI：`--date-review-budget N`）。缓存命中不占次数；设为 0 仅使用已有日期复核缓存。此项不限制内容分类请求。

“获取模型”成功不等于生成接口可用。客户端会自动协商 Chat Completions / Responses 与 JSON 输出模式，并识别误返回的网站 HTML 页面。调用失败标为**未完成复判**，不再写成模型认为应该排除。短篇验证方式见[模型连接检查](docs/model-connection.md)。

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

常用参数包括 `--no-llm`、`--no-browser-fallback`、`--download-attachments`、`--workers 1`、`--no-cache`、`--full-scan` 和 `--allow-rule-fallback`。默认不下载附件，完整列表见 `python main.py --help`。

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
