# GovPolicyWeekly v1.3.0

## English

Desktop layout fixes, linked PDF reports and recoverable collection tasks in the original glass-style workspace.

- Fix overlapping date presets and request-interval controls. Keep comfortable row spacing and scrolling at smaller window sizes, and align single-line and wrapped log messages.
- Support the standard window-close shortcut, including Command+W on macOS, with confirmation while collecting. Retain site selection without separate connectivity probes.
- Embed Source Han Sans CN in PDF reports, with compact section bands, shaded summaries and clickable original titles in both the index and article details.
- Add confirmed real model-call tests, saved task checkpoints, coverage details, interrupted-task recovery and retries for failed model decisions.

- Automatically negotiate Chat Completions / Responses and JSON output modes. Detect HTML returned by a website root, and try the same service's `/v1` path when appropriate.
- Separate unsuccessful model calls from valid decisions to exclude an article. Show successful and failed reviews in progress and saved run statistics.
- Use 410 core entries from the 703-entry, 30-site audit inventory; process each page immediately, with conservative date-window pagination and up to three sites in parallel.
- Reuse article/model caches across date ranges. Recent articles are re-fetched; older snapshots can be reused for up to seven days. Full-scan and no-cache controls remain available.
- Attachment downloads start off on every launch. When enabled, PDF export finishes before attachment downloads.

- **Installer:** `GovPolicyWeekly_Setup_1.3.0.exe`.
- **Portable:** fully extract `GovPolicyWeekly_windows_portable.zip`, then run `GovPolicyWeekly/GovPolicyWeekly.exe`. Keep all supporting folders.
- **Checksums:** `SHA256SUMS.txt`.

Windows 10/11 x64. No separate Python or LibreOffice installation is required for the packaged application or built-in PDF export. Browser fallback uses an installed Microsoft Edge or Google Chrome; Chromium is not bundled.

Provide your own model API URL and API key. Model charges are set by your provider. No personal API credentials or developer settings are distributed. Local API settings are masked in the interface but are not encrypted on disk.

Publication is gated on regression tests, local-fixture desktop integration, source and packaged-executable self-tests, a silent installer run followed by installed-application self-tests, and portable ZIP integrity checks. This does not certify access to every live website on every network. The Windows downloads are not code-signed, so SmartScreen may show an unrecognized-publisher warning.

## 简体中文

本版保留原有玻璃质感界面，更新界面排版、PDF 样式和任务恢复能力。

- 修复日期快捷按钮、请求间隔控件与下一行挤压的问题；统一控件间距，小窗口使用滚动展示，日志单行与多行保持对齐。
- 支持系统标准关闭快捷键（macOS 为 Command+W），采集过程中先确认再退出；移除独立连通检测，保留站点搜索和勾选。
- PDF 内嵌思源黑体，采用清晰的条目标题带和灰底摘要；信息清单与详情标题均可跳转原文。
- 增加需确认的实际模型调用测试、采集覆盖详情、任务检查点与断点恢复，支持仅重试失败的模型判断。

- 自动协商 Chat Completions / Responses 和 JSON 输出模式；识别错误返回的网站 HTML，必要时尝试同服务的 `/v1` 路径。
- 调用失败明确标为“未完成复判”，不再误写为“模型判断排除”；界面、日志和运行摘要分别统计成功与失败。
- 从 30 个网站的 703 个预设入口中使用 410 个核心入口；逐页处理，保守按日期停止历史翻页，最多三个站点并行。
- 正文和模型缓存跨日期范围复用；近期文章重新读取，较旧快照最多复用七天，保留完整遍历与禁用缓存的核对参数。
- 每次启动默认关闭附件下载；手动启用时先生成可打开的 PDF，再下载附件。

下载方式：

- `GovPolicyWeekly_Setup_1.3.0.exe`：安装版，双击安装后从开始菜单或桌面快捷方式打开。
- `GovPolicyWeekly_windows_portable.zip`：便携版，完整解压后打开 `GovPolicyWeekly/GovPolicyWeekly.exe`。
- `SHA256SUMS.txt`：下载文件的 SHA-256 校验值。

支持 Windows 10/11 64 位。无需安装 Python 或 LibreOffice，可直接生成 PDF。

本次发布使用系统 Microsoft Edge / Google Chrome 进行浏览器兜底，不随包携带 Chromium。
需要使用浏览器兜底时，请在运行软件的电脑上保留 Edge 或 Chrome。

启用大模型复判时，请在软件界面填写自己的 API URL、API Key 并获取模型。
软件不附带共享 API Key，模型调用费用由各自的 API 服务商收取。

旧报告不会自动补做模型复判；需要重新运行才能让之前调用失败的候选进入新版判断流程。

发布前执行回归测试、本地测试站点的桌面集成检查、源码与打包后 exe 自检、安装包静默安装及安装后程序自检，并检查便携 ZIP 完整性；自检涉及界面、时区、Excel、Word 和 PDF 导出。各政府网站的实际访问情况仍受网站状态和当前网络影响。

软件未进行代码签名，Windows SmartScreen 可能提示未知发布者。本地 API 配置虽在界面遮挡显示，但磁盘上的配置文件并未加密，请勿分享。
