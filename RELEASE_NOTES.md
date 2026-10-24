# GovPolicyWeekly v1.2.0

## English

Model API compatibility fixes and focused policy/personnel collection in the glass-style desktop workspace.

- Automatically negotiate Chat Completions / Responses and JSON output modes. Detect HTML returned by a website root, and try the same service's `/v1` path when appropriate.
- Separate unsuccessful model calls from valid decisions to exclude an article. Show successful and failed reviews in progress and saved run statistics.
- Use 410 core entries from the 703-entry, 30-site audit inventory; process each page immediately, with conservative date-window pagination and up to three sites in parallel.
- Reuse article/model caches across date ranges. Recent articles are re-fetched; older snapshots can be reused for up to seven days. Full-scan and no-cache controls remain available.
- Attachment downloads start off on every launch. When enabled, PDF export finishes before attachment downloads.

- **Installer:** `GovPolicyWeekly_Setup_1.2.0.exe`.
- **Portable:** fully extract `GovPolicyWeekly_windows_portable.zip`, then run `GovPolicyWeekly/GovPolicyWeekly.exe`. Keep all supporting folders.
- **Checksums:** `SHA256SUMS.txt`.

Windows 10/11 x64. No separate Python or LibreOffice installation is required for the packaged application or built-in PDF export. Browser fallback uses an installed Microsoft Edge or Google Chrome; Chromium is not bundled.

Provide your own model API URL and API key. Model charges are set by your provider. No personal API credentials or developer settings are distributed. Local API settings are masked in the interface but are not encrypted on disk.

Publication is gated on regression tests, local-fixture desktop integration, source and packaged-executable self-tests, a silent installer run followed by installed-application self-tests, and portable ZIP integrity checks. This does not certify access to every live website on every network. The Windows downloads are not code-signed, so SmartScreen may show an unrecognized-publisher warning.

## 简体中文

本版主要修复大模型接口调用，并包含政策、人事核心栏目采集优化。

- 自动协商 Chat Completions / Responses 和 JSON 输出模式；识别错误返回的网站 HTML，必要时尝试同服务的 `/v1` 路径。
- 调用失败明确标为“未完成复判”，不再误写为“模型判断排除”；界面、日志和运行摘要分别统计成功与失败。
- 从 30 个网站的 703 个预设入口中使用 410 个核心入口；逐页处理，保守按日期停止历史翻页，最多三个站点并行。
- 正文和模型缓存跨日期范围复用；近期文章重新读取，较旧快照最多复用七天，保留完整遍历与禁用缓存的核对参数。
- 每次启动默认关闭附件下载；手动启用时先生成可打开的 PDF，再下载附件。

下载方式：

- `GovPolicyWeekly_Setup_1.2.0.exe`：安装版，双击安装后从开始菜单或桌面快捷方式打开。
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
