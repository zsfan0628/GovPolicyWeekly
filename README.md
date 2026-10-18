# GovPolicyWeekly 政府政策周报生成工具

采集政府网站政策与人事任免信息，按日期、关键词和大模型复判筛选，生成带原文标题链接的 PDF 周报。

## Windows 下载

前往 [Releases 下载页](https://github.com/zsfan0628/GovPolicyWeekly/releases/latest)。

- 安装版：下载 `GovPolicyWeekly_Setup_*.exe`，双击安装。
- 便携版：下载 `GovPolicyWeekly_windows_portable.zip`，完整解压后打开文件夹里的 `GovPolicyWeekly.exe`。

支持 Windows 10/11 64 位，无需安装 Python 或 LibreOffice。
当前 GitHub 构建版使用电脑已安装的 Edge/Chrome 进行浏览器兜底。

启用大模型复判时，在界面填写自己的 API URL 和 API Key，点击“获取模型”后选择模型。
API Key 保存在自己电脑的 `user_settings.json`，不会随发布包分发；模型调用按服务商规则计费。

## 自动构建

GitHub Actions 使用标准 Windows 构建机器生成安装版和便携版。
维护者可以在 Actions 中手动运行 `Windows Build and Release` 获取测试包。
推送 `v1.0.0` 这样的版本标签时，会在检查通过后自动发布到 Releases。
构建包含软件启动、站点勾选、时区、Excel、Word 和 PDF 导出检查。

使用公开仓库和标准 GitHub 托管构建机器，可免费执行自动构建。
详细的本地打包与发布流程见 [WINDOWS_BUILD.md](WINDOWS_BUILD.md)。

## 核心逻辑

1. 脚本先粗筛候选网页。
2. 能确定的内容由规则硬通过：
   - 正式人事任免、任前公示、人选公示；
   - 政策栏目中的正式文种，例如通知、函、决定、公告、公示、通报、批复、意见、方案、办法、规定、解读等；
   - 农药经营许可、农药登记、行政许可、排污许可证等硬白名单事项。
3. 明显不是目标的内容直接排除：栏目页、首页、跳转页、普通会议新闻、视频、活动报道、单个项目环评受理/拟审查/审批公告等。
4. 剩下不好判断的候选才调用 GPT-5.5 复判。
5. GPT 未启用时，模糊候选默认不再兜底通过，避免“半信半疑”的内容进入报告。

## API 配置

桌面版直接在界面填写配置。命令行可以读取本地桌面配置，也支持环境变量：

```bash
export GOV_REPORT_OPENAI_API_KEY="你的API_KEY"
export GOV_REPORT_OPENAI_BASE_URL="https://你的服务地址/v1"
export GOV_REPORT_OPENAI_MODEL="你的模型名称"
```

源码不包含共享 API Key。`user_settings.json`、输出报告和构建缓存不应提交到 GitHub。

## 运行

```bash
python main.py --start-date 2026-05-23 --end-date 2026-05-29
```

## 图形界面测试版

本项目已提供一个轻量桌面界面，使用 Python 自带的 Tkinter，不需要额外安装 GUI 框架：

```bash
python app.py
```

界面支持通过紧凑下拉日历选择日期范围、勾选多个站点、选择输出目录，并可开关 GPT 复判、附件下载、浏览器兜底、严格模式等选项。点击“开始生成”后，会在窗口中实时显示 `main.py` 的运行日志。

图形界面会把 API URL、API Key、模型名等配置保存到本地 `user_settings.json`，下次打开无需重复输入。API Key 在界面中会用密码框形式隐藏显示。填写 API URL 和 API Key 后，可以点击“获取模型”读取模型列表，并从下拉框选择模型；如果服务商不开放模型列表接口，日志会显示具体请求地址和错误状态。

界面版默认按“无栏目/详情上限”运行，会尽量搜索所选站点发现到的全部栏目和详情页；因此选择全部站点时耗时可能明显增加。

### Windows 运行提示

PDF 可通过内置 reportlab 引擎直接生成，不再强制依赖 LibreOffice。若电脑上安装了 LibreOffice，程序会优先尝试把 DOCX 转成 PDF；没有 LibreOffice 时，会自动改用内置 PDF 引擎。

浏览器兜底依赖 Playwright。未安装 Playwright 时，普通网页采集仍可运行，但遇到需要浏览器访问的网站时兜底能力不可用。安装方式：

```bash
pip install playwright
python -m playwright install chromium
```

湖北部分政府站点可能对普通 requests 返回 412。v5.2 默认启用 Playwright 浏览器兜底；如果不想用浏览器兜底，可以关闭界面里的“浏览器兜底”，或在命令行使用 `--no-browser-fallback`。

如果不想用浏览器兜底：

```bash
python main.py --no-browser-fallback --start-date 2026-05-23 --end-date 2026-05-29
```

如果 GPT 没启用，但你仍想让模糊候选按规则兜底通过：

```bash
python main.py --allow-rule-fallback --no-llm --start-date 2026-05-23 --end-date 2026-05-29
```

不建议日常使用 `--allow-rule-fallback`，因为它可能把不确定内容收进报告。
