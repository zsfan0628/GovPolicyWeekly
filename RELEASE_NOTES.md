# GovPolicyWeekly v1.1.0

## English

New glass-style desktop workspace with real collection, model discovery, live progress, stop controls and report history. Includes highlighted 7-day / 30-day date presets and refreshed navigation for 30 configured government sites.

- **Installer:** `GovPolicyWeekly_Setup_1.1.0.exe`.
- **Portable:** fully extract `GovPolicyWeekly_windows_portable.zip`, then run `GovPolicyWeekly/GovPolicyWeekly.exe`. Keep all supporting folders.
- **Checksums:** `SHA256SUMS.txt`.

Windows 10/11 x64. No separate Python or LibreOffice installation is required for the packaged application or built-in PDF export. Browser fallback uses an installed Microsoft Edge or Google Chrome; Chromium is not bundled.

Provide your own model API URL and API key. Model charges are set by your provider. No personal API credentials or developer settings are distributed. Local API settings are masked in the interface but are not encrypted on disk.

Publication is gated on regression tests, local-fixture desktop integration, source and packaged-executable self-tests, a silent installer run followed by installed-application self-tests, and portable ZIP integrity checks. This does not certify access to every live website on every network. The Windows downloads are not code-signed, so SmartScreen may show an unrecognized-publisher warning.

## 简体中文

新增玻璃风格桌面工作台，已连接真实采集、模型获取、实时进度、停止任务与历史报告。包含带选中高亮的“近 7 天 / 近 30 天”，以及 30 个政府站点的最新栏目导航适配。

下载方式：

- `GovPolicyWeekly_Setup_1.1.0.exe`：安装版，双击安装后从开始菜单或桌面快捷方式打开。
- `GovPolicyWeekly_windows_portable.zip`：便携版，完整解压后打开 `GovPolicyWeekly/GovPolicyWeekly.exe`。
- `SHA256SUMS.txt`：下载文件的 SHA-256 校验值。

支持 Windows 10/11 64 位。无需安装 Python 或 LibreOffice，可直接生成 PDF。

本次发布使用系统 Microsoft Edge / Google Chrome 进行浏览器兜底，不随包携带 Chromium。
需要使用浏览器兜底时，请在运行软件的电脑上保留 Edge 或 Chrome。

启用大模型复判时，请在软件界面填写自己的 API URL、API Key 并获取模型。
软件不附带共享 API Key，模型调用费用由各自的 API 服务商收取。

发布前执行回归测试、本地测试站点的桌面集成检查、源码与打包后 exe 自检、安装包静默安装及安装后程序自检，并检查便携 ZIP 完整性；自检涉及界面、时区、Excel、Word 和 PDF 导出。各政府网站的实际访问情况仍受网站状态和当前网络影响。

软件未进行代码签名，Windows SmartScreen 可能提示未知发布者。本地 API 配置虽在界面遮挡显示，但磁盘上的配置文件并未加密，请勿分享。
