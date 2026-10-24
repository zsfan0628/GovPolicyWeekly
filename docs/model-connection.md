# Model Connection Checks / 模型连接检查

## Why Model Discovery Can Work While Generation Fails

模型列表是 `GET /models`，文章判断使用 `POST /chat/completions` 或 `POST /responses`。
第三方兼容服务可能支持其中一个生成接口，或要求 `/v1` 路径。HTTP 200 只表示
服务器返回了内容；如果内容是 HTML 首页，不代表模型生成成功。

2026-10-24 排查中，用户配置的根地址下 `/chat/completions` 实际返回 HTTP 200
和 `text/html`，导致旧版 JSON 解码失败。短请求已确认同服务 `/v1/chat/completions`
可返回模型文本；修复后实际分类测试通过根地址下的 Responses 接口获得有效判断。
本文不记录私人服务地址、密钥或账户信息。

## Current Behavior

- 默认 `auto`：尝试当前服务的 Chat Completions 和 Responses，根地址没有路径时
  也允许同一服务的 `/v1`。不猜测其他域名，不转发凭证到新的服务，不自动跟随跳转。
- 显式设置 `GOV_REPORT_OPENAI_API_STYLE=chat_completions` 或 `responses` 时保留所选类型。
- 在严格 JSON Schema、普通 JSON、提示词要求 JSON 三种模式间切换。
  HTTP 200 的空内容、非法 JSON 或字段不符也会触发输出模式切换。
- 已成功的路径和模式在本次运行中复用。不会替换用户所选模型。
- 拒答、截断、缺少必要字段或把布尔值写成字符串不算成功复判。
- 日志只记录状态、响应类型和错误类别，不写服务器原始回答、HTML 页面或请求凭证。
- 401/402/403 明确提示检查密钥、余额和生成权限，不重复发送；网络错误、429 和
  服务器临时错误按配置限制重试次数。调用失败不缓存为长期排除结论。
- 日志和 `runtime_summary.json` 分开统计成功复判、失败、缓存。正常判断为不收录
  也算成功复判；错误导致暂不收录则明确写为“未完成复判”。

OpenAI's official documentation describes the two response envelopes and their
different structured-output parameters. Third-party service compatibility is
verified by tests rather than inferred from model-list access:
[Responses migration guide](https://developers.openai.com/api/docs/guides/migrate-to-responses),
[Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

## Short Live Test

在项目的 Python 环境运行：

```bash
python scripts/test_model_connection.py
```

脚本读取桌面软件已保存的地址、密钥和模型，用一个短篇虚构样例验证完整分类流程，
不抓网站、不生成完整报告、不改写原有报告和设置，也不保存模型判断缓存。
**这会调用你配置的真实模型服务，可能产生少量费用。** 输出 `ok: true` 才表示已经
获得字段校验通过的判断，而不只是列出了模型。样例是否被判定为收录不影响连接测试。

显示 `api_style: responses` 时，说明使用 Responses 接口；`api_prefix: /v1`
表示尝试了同源补充路径，`configured` 表示使用配置地址的根路径。

```bash
python -m unittest discover -s tests -v
python desktop_app.py --smoke-test --artifacts release-check/model-integration
```

以上单元测试和桌面集成测试均使用模拟响应或本地服务，不调用付费 API。
旧输出目录不会被自动修正。过去调用失败的文章需重新运行复判，不能因为软件修复
就把旧报告标为已完成模型审核。旧 Windows exe 同样需要重新构建后才包含这些修复。
