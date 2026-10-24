# Collection Performance / 采集性能与核对

## Scope

`config/sources.yaml` retains the 30-site, 703-entry audit inventory. It is not
an inventory of every clickable item on those sites. `config/crawl_scope.yaml`
contains an exact-name allowlist for daily policy/personnel columns; currently
410 configured entries match it. The original entries are not deleted.

日常不再从每个首页广泛展开。只访问核心入口、符合白名单且位于核心分支内的
子栏目，以及它们的分页。混合的通知公告栏目保留；生活资讯、来信、招标中标、
单个项目环评公示等不在核心栏目白名单中。核心栏目仍可能包含非目标文章，
正文分类规则和模型复判继续生效。没有栏目名称资料的自定义站点保留原发现方式。

## Date Windows

每页读完即处理候选文章，不再等待整个站点历史列表遍历完。
有可靠列表日期且超出区间的文章不进入正文抓取；仅从 URL 或标题猜到的日期
不足以直接跳过正文。列表的独立日期元素优先于标题里提及的历史日期。

日期停止翻页依据运行中观察到的排序，不是网站提供的完整性保证：

- 同一分页链至少读取三页，每页至少两条非置顶候选。
- 所有普通候选均有可靠日期，页内及跨页保持倒序。
- 连续至少两页普通候选全部早于开始日期，才不再请求下一页。
- 置顶条目仍检查，但不用于判断列表是否已越过日期窗口。
- 日期缺失、只有一条普通候选或日期逆序时，该链不进行日期提前停止。
- 重复分页保护仍保留，并继续支持 JCMS 首组衔接。

异常置顶标记、后续分页突然插入新文章、网页结构变化仍可能造成漏检。
完整性核对可用 `--full-scan --no-cache`；它也不能突破登录、验证码或不可访问页面。

## Concurrency and Cache

默认同时采集最多三个站点。每个采集线程独立持有 HTTP 会话和浏览器上下文；
同一配置主机的任务串行，单站请求间隔仍有效。模型请求最多两个并发。
最终按配置站点顺序合并，避免完成先后改变去重保留顺序。

缓存位于输出根目录的 `.cache/`，不随日期范围重新建立：

- 正文快照保存在 SQLite 中，仅保存成功提取、正文至少 80 字且有日期的文章。
- 发布不足 48 小时、缺失日期或快照已满七天的文章重新抓取。
- 每次仍重新检查日期和规则；不是把上一次报告原样复制到新日期。
- 模型缓存键包含模型、接口、提示词、结构、正文和规则初判。
- 网络失败和模型调用失败不保存为长期排除结果。缓存不可写时继续正常采集。

较旧文章在七天内的更正可能暂时不被发现；需要最新正文时使用 `--no-cache`。
缓存包含公开文章内容和模型判断，也应按本地报告资料保管，不要上传至仓库。

## Attachments and Progress

所有桌面入口每次启动默认关闭附件下载，命令行默认同样不下载。
关闭只是不进行新的下载，不会删除过去已下载的文件。原始附件链接仍保留。

显式开启后先导出 PDF，界面出现“打开本次 PDF”；随后执行单独的附件阶段。
下载结果记录在 `attachment_downloads.json`，同时更新 `data.json` 的本地路径。
附件失败显示警告，不撤销已生成的 PDF。附件仍未下载完时关闭软件会停止下载。

界面和 `runtime_summary.json` 分别统计列表、正文、模型及附件数量、耗时、
缓存命中和错误。并行阶段显示累计任务耗时，不能简单相加当作总运行时长。

## Verification

```bash
python -m unittest discover -s tests -v
python desktop_app.py --smoke-test --artifacts release-check/performance-desktop

# Maintenance comparison; may take much longer than a daily run.
python main.py --start-date 2026-10-17 --end-date 2026-10-23 --full-scan --no-cache --workers 1

# Download attachments only when explicitly requested.
python main.py --days 7 --download-attachments
```

本地分页对照样例中，核心模式与完整遍历均收录同样两篇目标文章，访问次数从
14 次减至 5 次；这只是可重复的离线测试，不是对真实三十站的测速承诺。
桌面集成检查使用本地 HTTP 和模型服务，不调用真实用户的付费 API。

本次源码修改不会自动更新旧版 Windows exe；发布前仍需重新进行 Windows 构建测试。
