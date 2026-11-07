# Task Coverage and Recovery / 采集覆盖与任务恢复

## Model Probe / 测试实际调用

The desktop's **测试实际调用** button sends a short fictional example to the selected
model using the same transport negotiation, classification schema and validation as
collection. It does not use judgment caches or send collected articles. Confirmation
is required because a real provider may charge for the requests. Compatibility
negotiation and retries may produce more than one request; the desktop stops the
probe after 180 seconds. A valid exclusion is a successful connection test, not a
failure. Success is evidence for that configuration at that moment, not a guarantee
that the provider will remain available or that every classification is correct.

填写 URL、API Key 并选择模型后，点击“测试实际调用”，确认少量 API 用量提示。
软件会显示调用是否成功、耗时、接口类型和输出模式。返回空白、HTML、非法 JSON、
缺少字段、认证失败或超时都不能算通过。修改连接配置后，原测试结果会标记为过期。
API Key 不会写入测试命令行或任务断点文件。

## Coverage / 采集完整性

The task panel distinguishes completed, partially failed, inaccessible and unfinished
sources. **任务详情与恢复** expands each source into visited list URLs, column names,
errors, date-window or repeated-pagination stops, and failed article/model reviews.
A PDF can exist while collection is incomplete; the interface reports this explicitly.
Empty HTML with no extractable links is flagged for inspection rather than counted
as a successful zero-result source.

“完成”仅表示本次配置范围内的遍历没有已知失败，不代表核验了网站所有内容，也不
保证网站没有未识别的栏目。候选“排除”可能包含列表阶段排除；“日期范围外”单独统计，
不能把所有候选数当成日期内文章数。手工补充链接存在时作为单独来源显示。
`coverage_summary.json` 保存累计结果；`runtime_summary.json` 的阶段耗时和模型调用数
属于本次执行尝试，恢复任务时不代表整个任务历史的 API 用量。

## Recovery / 恢复与重试

- **继续／补采失败项** uses the original dates, selected sources and classification
  rules. Completed sources and successful decisions are reused; successfully fetched
  list snapshots are replayed locally to reconstruct traversal. Missing and failed
  pages are fetched again. Failed model reviews reuse saved article bodies.
- **仅重试模型** processes only stored `llm_failed` articles, without website requests.
  Existing included and excluded results remain in the task. The current API URL,
  key and selected model are used; previously successful decisions are not rejudged.
- Restarting the app restores the most recent task pointer. These checkpoints only
  exist for tasks started with this implementation; older reports cannot be resumed.
- New tasks write separate `task-...` directories under the date range. Recovery
  regenerates the original task's report without overwriting other tasks.
- A process lock prevents two workers from recovering the same task simultaneously.

恢复按钮针对“最近任务”，不是界面上新选的日期或站点；弹窗会显示原任务日期。
如果要按新范围采集，或要让新模型重新判断全部文章，请点击“开始生成”新建任务。
复用的是原任务时点的网页快照，不会重新核验已经成功处理的页面是否发生更正。
当前界面不提供任意历史任务切换；命令行可通过 `--resume-task` 指定旧断点文件。
若采集规则、关键词或任务文件损坏导致无法恢复，应新建任务，不能混用结果。

Checkpoints are local SQLite files in the desktop user-data `runtime` folder (or the
CLI output directory). They contain public page snapshots, article text, decisions
and output paths, not API credentials. Do not upload the user-data folder, reports or
checkpoint files to a public repository. Deleting checkpoints disables recovery;
the app does not automatically delete them during this version's operation.

## Website Changes / 网站异常怎么处理

本版提供采集过程中的覆盖和失败记录，不是独立的全站健康巡检器，也不会自动修改
网站配置。临时故障先重试；栏目地址变化一般需要维护 `sources.yaml` 或
`crawl_scope.yaml`；页面解析结构或动态接口变化可能需要修复解析代码并重新发布。
已打包版本尚无配置在线更新机制，不能理解为网站改版后软件会自动修复。

Offline tests use local HTTP fixtures and mocked model responses. They do not call
the user's paid API or certify all thirty live websites.
