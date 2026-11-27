改进发布日期核查，并修复桌面导航按钮的双重轮廓。

## English

- Disputed publication dates can be checked against quoted page evidence. Unconfirmed historical clues are kept separate from inaccessible pages.
- Model date reviews are unlimited by default. An optional task-wide request cap survives resume; cache hits do not consume it. Unresolved pages remain available for review.
- Navigation now uses a single rounded selection background for mouse input and a matching keyboard focus outline.

## 简体中文

- 发布日期有争议时，可以让模型复核网页引文。未确认的历史线索与无法访问的页面分开记录。
- 日期复核默认不限次数。可在“模型复判”中设置整次任务的请求上限；缓存命中不占次数，断点续跑保留已用次数。超出上限的文章保留待核查。
- 导航按钮的选中底色与键盘焦点框统一圆角，鼠标点击不再叠加红框。

## Windows x64 downloads / 下载

| File | Purpose / 用途 |
| --- | --- |
| `GovPolicyWeekly_Setup_1.5.2.exe` | Installer / 安装版 |
| `GovPolicyWeekly_windows_portable.zip` | Extract the entire folder before running / 便携版，完整解压后再运行 |
| `GovPolicyWeekly_windows_source.zip` | Source and Windows build scripts / 源码与 Windows 构建脚本 |
| `SHA256SUMS.txt` | Verify the three downloads / 三个下载包的 SHA-256 |
| `program-update.json` | In-app update metadata / 软件更新清单 |

The installer and portable build do not require Python or LibreOffice. Browser fallback uses an installed Edge or Chrome. Model review requires your own API credentials.

安装版和便携版无需另装 Python 或 LibreOffice。浏览器兜底使用系统已有的 Edge 或 Chrome；使用模型复判需自备 API 配置。Windows 可能对未签名的安装程序显示 SmartScreen 提示。
