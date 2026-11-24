# GovPolicyWeekly v1.5.0

## English

- The new pearl-gray and dusty-rose desktop opens with a world map that zooms into China without hiding the surrounding geography. Skip the animation or enable reduced motion.
- The collection calendar highlights the actual date range, including both endpoints. Open the latest local report by its dates instead of its week number.
- Site-level activity is shown separately from detailed diagnostics. This release does not claim a measured improvement in live-site retrieval accuracy.

## 简体中文

- 桌面恢复珍珠灰与雾玫瑰配色。启动时从世界地图推近中国，保留周边陆地，再由细颗粒聚成「政策周报」。支持跳过及减少动态效果。
- 月历高亮实际查询范围（含首尾），跨月翻页不会改变查询条件。「最近一期」按日期打开 PDF，不再显示周次。
- 采集任务按站点展示动态，可切换查看技术明细。本次没有进行新旧版本真实网站命中率对照测试。

## Windows x64 downloads / 下载

| File | Purpose / 用途 |
| --- | --- |
| `GovPolicyWeekly_Setup_1.5.0.exe` | Installer / 安装版 |
| `GovPolicyWeekly_windows_portable.zip` | Extract the entire folder before running / 便携版，完整解压后再运行 |
| `GovPolicyWeekly_windows_source.zip` | Source and Windows build scripts / 源码与 Windows 构建脚本 |
| `SHA256SUMS.txt` | Verify the three downloads / 三个下载包的 SHA-256 |
| `program-update.json` | In-app update metadata / 软件更新清单 |

The installer and portable build do not require Python or LibreOffice. Browser fallback uses an installed Edge or Chrome. Model review requires your own API credentials.

安装版和便携版无需另装 Python 或 LibreOffice。浏览器兜底使用系统已有的 Edge 或 Chrome；使用模型复判需自备 API 配置。Windows 可能对未签名的安装程序显示 SmartScreen 提示。
