# 30 个政府网站栏目与控件检查记录（2026-10-18）

检查对象为软件 config/sources.yaml 中的 30 个站点。逐站请求当前公开页面，保存栏目、按钮、检索表单、下拉选项、iframe 和脚本信息，并抽查列表翻页及详情页。

范围说明：主检查从首页与配置入口递归两层，部分动态目录另做补查；不等同于对政府网站所有历史页面或全部业务功能进行人工验收。按钮/表单项记录其入口和参数，未填写或提交登录、申请、举报、缴费等表单，也未使用个人 API Key。

控件数量是逐页累计记录，同一导航会在多个页面重复出现；HTTP 可达、页面可解析与按钮业务功能正常是不同检查项。

页面记录按站点和请求 URL 去重，包含栏目、公开接口及详情抽样；HTTP/HTTPS 别名可能分开计数。非 HTML 附件不作为网页失败统计，修复前拼接错误的目录地址由重查结果替代，原始记录仍保留。

## 逐站结果

| # | 网站 | 页面检查 | 页面可达 | 失败/待复核 | 控件记录 | 已验证采集入口 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 中华人民共和国农业农村部 | 1634 | 1624 | 10 | 55389 | 78 |
| 2 | 江苏省农业农村厅 | 123 | 122 | 1 | 2603 | 16 |
| 3 | 湖北省农业农村厅 | 341 | 341 | 0 | 4542 | 19 |
| 4 | 黑龙江省农业农村厅 | 219 | 219 | 0 | 4676 | 16 |
| 5 | 南通市农业农村局 | 74 | 74 | 0 | 2205 | 7 |
| 6 | 国家发展和改革委员会 | 546 | 546 | 0 | 4229 | 31 |
| 7 | 江苏省发展和改革委员会 | 70 | 70 | 0 | 208 | 8 |
| 8 | 湖北省发展和改革委员会 | 659 | 659 | 0 | 23117 | 61 |
| 9 | 黑龙江省发展和改革委员会 | 167 | 167 | 0 | 4685 | 10 |
| 10 | 南通市发展和改革委员会 | 64 | 64 | 0 | 1960 | 7 |
| 11 | 中华人民共和国生态环境部 | 1623 | 1622 | 1 | 11554 | 143 |
| 12 | 江苏省生态环境厅 | 151 | 151 | 0 | 1411 | 16 |
| 13 | 湖北省生态环境厅 | 454 | 454 | 0 | 10170 | 31 |
| 14 | 黑龙江省生态环境厅 | 219 | 217 | 2 | 5160 | 15 |
| 15 | 南通市生态环境局 | 75 | 75 | 0 | 2404 | 7 |
| 16 | 中华人民共和国应急管理部 | 629 | 629 | 0 | 9369 | 25 |
| 17 | 江苏省应急管理厅 | 94 | 94 | 0 | 860 | 3 |
| 18 | 湖北省应急管理厅 | 317 | 317 | 0 | 5740 | 15 |
| 19 | 黑龙江省应急管理厅 | 209 | 209 | 0 | 6633 | 20 |
| 20 | 南通市应急管理局 | 62 | 62 | 0 | 1593 | 7 |
| 21 | 中华人民共和国工业和信息化部 | 277 | 277 | 0 | 4399 | 17 |
| 22 | 江苏省工业和信息化厅 | 121 | 121 | 0 | 1011 | 17 |
| 23 | 湖北省经济和信息化厅 | 488 | 487 | 1 | 9801 | 28 |
| 24 | 黑龙江省工业和信息化厅 | 163 | 163 | 0 | 5001 | 11 |
| 25 | 南通市工业和信息化局 | 57 | 57 | 0 | 2323 | 5 |
| 26 | 中华人民共和国财政部 | 1165 | 1165 | 0 | 8562 | 25 |
| 27 | 江苏省财政厅 | 130 | 130 | 0 | 1448 | 15 |
| 28 | 湖北省财政厅 | 368 | 368 | 0 | 6099 | 24 |
| 29 | 黑龙江省财政厅 | 200 | 199 | 1 | 5051 | 17 |
| 30 | 南通市财政局 | 115 | 112 | 3 | 2709 | 9 |

## 本地修复

- 解析江苏 JCMS 列表中脚本/XML 的记录与翻页入口。
- 读取公共脚本中写入的导航，跟随同站点桌面跳转。
- 递归发现子栏目，处理普通下一页、TRS 分页及 JCMS 分组分页。
- 识别黑龙江动态分类和公开列表查询接口，保留发布日期并继续分页。
- 读取南通脚本生成的折叠菜单和 TrueCMS 分组记录，保留检索与下拉选项。
- 适配工信部政策文件库公开查询及动态栏目接口；湖北 h5 列表不再被误当文章。
- 对工信部等动态列表及访问校验页面使用浏览器渲染；浏览器仍报错时明确记录失败。
- 栏目、分页链接不再作为详情页重复抓取，文章日期优先使用发布元数据。
- 0 表示不限制栏目/详情数量；已有 UI 的无上限模式同步使用该值。

## 入口与异常明细

### 01 中华人民共和国农业农村部

- 首页：https://www.moa.gov.cn/
- 浏览器渲染/兜底页面：25。
- 已核验入口：[聚焦2026年中央一号文件](https://www.moa.gov.cn/ztzl/jj2026nzyyhwj/)
- 已核验入口：[进一步规范农药兽药生产经营使用综合整治行动](https://www.moa.gov.cn/ztzl/nsyzhzz/)
- 已核验入口：[政策法规](https://www.moa.gov.cn/gk/zcfg/)
- 已核验入口：[通知公告](https://www.moa.gov.cn/gk/tzgg_1/)
- 已核验入口：[人事信息](https://www.moa.gov.cn/gk/rsxx_1/)
- 已核验入口：[人事司（党组巡视工作领导小组办公室）](https://rss.moa.gov.cn/)
- 已核验入口：[法规司](https://fgs.moa.gov.cn/)
- 已核验入口：[政策与改革司](https://zcggs.moa.gov.cn/)
- 已核验入口：[农业农村部规章](https://www.moa.gov.cn/gk/nyncbgzk/)
- 已核验入口：[公告](https://www.moa.gov.cn/gk/tzgg_1/gg/)
- 已核验入口：[通知](https://www.moa.gov.cn/gk/tzgg_1/tz/)
- 已核验入口：[行政法规](https://www.moa.gov.cn/gk/zcfg/xzfg/)
- 已核验入口：[部门规章](https://www.moa.gov.cn/gk/zcfg/gfxwj/)
- 已核验入口：[规范性文件](https://www.moa.gov.cn/gk/zcfg/nybgz/)
- 已核验入口：[政策](https://www.moa.gov.cn/gk/zcfg/qnhnzc/)
- 已核验入口：[政策解读](https://www.moa.gov.cn/gk/zcjd/)
- 已核验入口：[涉企行政检查公示](https://www.moa.gov.cn/ztzl/sqxzjcgs/)
- 已核验入口：[法律法规](https://www.moa.gov.cn/ztzl/nsyzhzz/flfgzcxc/)
- 已核验入口：[政策法规](https://www.moa.gov.cn/ztzl/zhnyzxd/zcfg/zybs/)
- 已核验入口：[部门政策](https://www.moa.gov.cn/ztzl/zhnyzxd/zcfg/bmzc/)
- 已核验入口：[地方政策](https://www.moa.gov.cn/ztzl/zhnyzxd/zcfg/dfzc/)
- 已核验入口：[法律法规](https://www.moa.gov.cn/ztzl/zhnyzxd/zcfg/zybs/flfg/)
- 已核验入口：[中央政策](https://www.moa.gov.cn/ztzl/zhnyzxd/zcfg/zybs/zyzc/)
- 已核验入口：[标准规范](https://www.moa.gov.cn/ztzl/zhnyzxd/bzgf/)
- 已核验入口：[标准工作](https://www.moa.gov.cn/ztzl/zhnyzxd/bzgf/bzzj/)
- 已核验入口：[重要政策](https://www.moa.gov.cn/ztzl/szcpxx/zyzc/)
- 已核验入口：[重要文件](https://www.moa.gov.cn/ztzl/dscqgtrpc/zywj/)
- 已核验入口：[人事司](https://www.moa.gov.cn/govpublic/1/2/4/index.htm?id=4)
- 已核验入口：[法规司](https://www.moa.gov.cn/govpublic/1/2/5/index.htm?id=5)
- 已核验入口：[政策与改革司](https://www.moa.gov.cn/govpublic/1/2/78/index.htm?id=78)
- 已核验入口：[人事管理类](https://www.moa.gov.cn/govpublic/22/24/index.htm?id=24)
- 已核验入口：[政策法规类](https://www.moa.gov.cn/govpublic/22/71/index.htm?id=71)
- 已核验入口：[行政审批类](https://www.moa.gov.cn/govpublic/22/28/index.htm?id=28)
- 已核验入口：[农业标准类](https://www.moa.gov.cn/govpublic/22/31/index.htm?id=31)
- 已核验入口：[农业农村部公告](https://www.moa.gov.cn/govpublic/37/39/index.htm?id=39)
- 已核验入口：[农业农村部文件](https://www.moa.gov.cn/govpublic/37/40/index.htm?id=40)
- 已核验入口：[农业农村部办公厅文件](https://www.moa.gov.cn/govpublic/37/41/index.htm?id=41)
- 已核验入口：[国新办举行切实做好长江流域禁捕工作国务院政策例行吹风会](https://www.moa.gov.cn/hd/zbft_news/cjlyjb/)
- 已核验入口：[农业部就进一步禁用和淘汰高毒农药有关情况举行发布会](https://www.moa.gov.cn/hdllm/wszb/zb38/)
- 已核验入口：[通知公告](https://rss.moa.gov.cn/tzgg/)
- 已核验入口：[政策解读](https://rss.moa.gov.cn/zcjd/)
- 已核验入口：[法律法规](https://fgs.moa.gov.cn/flfg/)
- 已核验入口：[行政审批](https://fgs.moa.gov.cn/xzsp/)
- 已核验入口：[通知公告](https://zcggs.moa.gov.cn/tzgg/)
- 已核验入口：[政策之窗](https://zcggs.moa.gov.cn/zczc/)
- 已核验入口：[政策调研与软科学管理](https://zcggs.moa.gov.cn/zcyjyrkxgl/)
- 已核验入口：[通知公告](https://jhs.moa.gov.cn/tzgg/)
- 已核验入口：[政策解读](https://jcs.moa.gov.cn/zcjd/)
- 已核验入口：[政策解读](https://shsys.moa.gov.cn/zcjd/)
- 已核验入口：[政策解读](https://bfs.moa.gov.cn/zcjd/)
- 已核验入口：[政策文件](https://jdjcs.moa.gov.cn/zcwj/)
- 已核验入口：[政策解读](https://jgs.moa.gov.cn/zcjd/)
- 已核验入口：[农业标准](https://jgs.moa.gov.cn/nybz/)
- 已核验入口：[政策解读](https://nkj.moa.gov.cn/zcjd/)
- 已核验入口：[政策发布](https://ntjss.moa.gov.cn/zcfb/)
- 已核验入口：[通知公告](https://ntjss.moa.gov.cn/tzgg/)
- 已核验入口：[聚焦2024中央一号文件](https://www.moa.gov.cn/ztzl/2024yhwj/)
- 已核验入口：[聚焦2020年中央一号文件](https://www.moa.gov.cn/ztzl/jj2020zyyhwj/)
- 已核验入口：[聚焦2019年中央一号文件](https://www.moa.gov.cn/ztzl/jj2019zyyhwj/)
- 已核验入口：[化肥农药减量在行动](https://www.moa.gov.cn/ztzl/nyhfjlzxd/)
- 已核验入口：[聚焦2016中央一号文件](https://www.moa.gov.cn/ztzl/2016zyyhwj/)
- 已核验入口：[聚焦2015中央一号文件](https://www.moa.gov.cn/ztzl/yhwj2015/)
- 已核验入口：[防治艾滋病知识和政策](https://www.moa.gov.cn/ztzl/fzazbzshzc/)
- 已核验入口：[农业基本建设项目管理法规选编](https://www.moa.gov.cn/ztzl/nyjbjsxmglfgxb/)
- 已核验入口：[农业国内支持政策研究](https://www.moa.gov.cn/ztzl/nygnzczcyj/)
- 已核验入口：[政策解读](https://dangwei.moa.gov.cn/zcjd/)
- 已核验入口：[通知公告](https://dangwei.moa.gov.cn/tzgg/)
- 已核验入口：[聚焦2025年中央一号文件](https://www.moa.gov.cn/ztzl/2025yhwj/)
- 已核验入口：[聚焦2023中央一号文件](https://www.moa.gov.cn/ztzl/2023yhwj/)
- 已核验入口：[聚焦2022中央一号文件](https://www.moa.gov.cn/ztzl/jj2022zyyhwj/)
- 已核验入口：[聚焦2021年中央一号文件](https://www.moa.gov.cn/ztzl/jj2021zyyhwj/)
- 已核验入口：[2019年度“全国十佳农民”资助项目人选公示](https://www.moa.gov.cn/ztzl/2019sjnm/)
- 已核验入口：[聚焦2018年中央一号文件](https://www.moa.gov.cn/ztzl/yhwj2018/)
- 已核验入口：[聚焦2014中央一号文件](https://www.moa.gov.cn/ztzl/yhwj2014/)
- 已核验入口：[聚焦2013中央一号文件](https://www.moa.gov.cn/ztzl/yhwj2013/)
- 已核验入口：[聚焦2012中央一号文件](https://www.moa.gov.cn/ztzl/yhwj/)
- 已核验入口：[落实政策措施力夺秋粮丰收](https://www.moa.gov.cn/ztzl/jqkxgl/)
- 已核验入口：[2010:党的强农惠农政策](https://www.moa.gov.cn/ztzl/2010qnhn/)
- 待复核：[页面](https://data.moa.gov.cn/misportal/public/agriculture200Helper.jsp)；HTTPSConnectionPool(host='data.moa.gov.cn', port=9443): Max retries exceeded with url: /misportal/public/agriculture200Helper.jsp (Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1028)')))
- 待复核：[页面](https://www.moa.gov.cn/xw/lzjs/202609/t20260909_6487527.htm)；HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Max retries exceeded with url: /xw/lzjs/202609/t20260909_6487527.htm (Caused by ReadTimeoutError("HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Read timed out. (read timeout=12)"))
- 待复核：[页面](https://www.moa.gov.cn/ztzl/2022qcz/index_1.htm)；HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Max retries exceeded with url: /ztzl/2022qcz/index_1.htm (Caused by ReadTimeoutError("HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Read timed out. (read timeout=12)"))
- 待复核：[页面](https://www.moa.gov.cn/ztzl/2020cg/)；HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Max retries exceeded with url: /ztzl/2020cg/ (Caused by ReadTimeoutError("HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Read timed out. (read timeout=12)"))
- 待复核：[页面](https://www.moa.gov.cn/ztzl/2019dnq/index_1.htm)；HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Max retries exceeded with url: /ztzl/2019dnq/index_1.htm (Caused by ReadTimeoutError("HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Read timed out. (read timeout=12)"))
- 待复核：[页面](https://www.moa.gov.cn/ztzl/2014lhjj/)；HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Max retries exceeded with url: /ztzl/2014lhjj/ (Caused by ReadTimeoutError("HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Read timed out. (read timeout=12)"))
- 待复核：[页面](https://www.moa.gov.cn/ztzl/nyncggfz30n_1/gd/index_1.htm)；HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Max retries exceeded with url: /ztzl/nyncggfz30n_1/gd/index_1.htm (Caused by ReadTimeoutError("HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Read timed out. (read timeout=12)"))
- 待复核：[页面](https://www.moa.gov.cn/xw/shipin/xwzx/202602/t20260204_6481307.htm)；HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Max retries exceeded with url: /xw/shipin/xwzx/202602/t20260204_6481307.htm (Caused by ReadTimeoutError("HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Read timed out. (read timeout=12)"))
- 待复核：[页面](https://fgs.moa.gov.cn/gzdt/202511/t20251128_6479291.htm)；HTTPSConnectionPool(host='fgs.moa.gov.cn', port=443): Max retries exceeded with url: /gzdt/202511/t20251128_6479291.htm (Caused by ReadTimeoutError("HTTPSConnectionPool(host='fgs.moa.gov.cn', port=443): Read timed out. (read timeout=12)"))
- 待复核：[页面](https://www.moa.gov.cn/ztzl/sdxf/200608/t20060814_667339.htm)；HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Max retries exceeded with url: /ztzl/sdxf/200608/t20060814_667339.htm (Caused by ReadTimeoutError("HTTPSConnectionPool(host='www.moa.gov.cn', port=443): Read timed out. (read timeout=12)"))

### 02 江苏省农业农村厅

- 首页：https://nynct.jiangsu.gov.cn/
- 浏览器渲染/兜底页面：1。
- 已核验入口：[农田建设制度标准](https://nynct.jiangsu.gov.cn/col/col13474/index.html)
- 已核验入口：[法律法规](https://nynct.jiangsu.gov.cn/col/col51437/index.html)
- 已核验入口：[现行规章](https://nynct.jiangsu.gov.cn/col/col51442/index.html)
- 已核验入口：[行政规范性文件](https://nynct.jiangsu.gov.cn/col/col51439/index.html)
- 已核验入口：[政策解读](https://nynct.jiangsu.gov.cn/col/col51447/index.html)
- 已核验入口：[政策问答](https://nynct.jiangsu.gov.cn/col/col12553/index.html)
- 已核验入口：[通知](https://nynct.jiangsu.gov.cn/col/col12094/index.html)
- 已核验入口：[公告](https://nynct.jiangsu.gov.cn/col/col12095/index.html)
- 已核验入口：[检查标准](https://nynct.jiangsu.gov.cn/col/col12137/index.html)
- 已核验入口：[农业标准](https://nynct.jiangsu.gov.cn/col/col11972/index.html)
- 已核验入口：[政策规定](https://nynct.jiangsu.gov.cn/col/col66239/index.html)
- 已核验入口：[通知公告](https://nynct.jiangsu.gov.cn/col/col11977/index.html)
- 已核验入口：[涉企行政检查公示专栏](https://nynct.jiangsu.gov.cn/col/col11999/index.html)
- 已核验入口：[省本级办理许可统计](https://nynct.jiangsu.gov.cn/col/col12411/index.html)
- 已核验入口：[网上公示](https://nynct.jiangsu.gov.cn/col/col51459/index.html)
- 已核验入口：[省级政策制度](https://nynct.jiangsu.gov.cn/col/col15425/index.html)
- 待复核：[页面](https://nynct.jiangsu.gov.cn/col/col87855/)；浏览器仍未通过站点访问校验: https://nynct.jiangsu.gov.cn/col/col87855/

### 03 湖北省农业农村厅

- 首页：https://nyt.hubei.gov.cn/
- 浏览器渲染/兜底页面：3。
- 已核验入口：[通知公告](https://nyt.hubei.gov.cn/zfxxgk/zc_GK2020/qtzdgkwj_GK2020/)
- 已核验入口：[政策解读](https://nyt.hubei.gov.cn/zfxxgk/zc_GK2020/zcjd_GK2020/)
- 已核验入口：[政策问答平台](https://nyt.hubei.gov.cn/bmdt/ztzl/zxzt/zcwd/)
- 已核验入口：[农药兽药生产经营使用综合整治行动](https://nyt.hubei.gov.cn/bmdt/ztzl/zxzt/nysyzhzzxd/)
- 已核验入口：[行政规范性文件库](https://nyt.hubei.gov.cn/bmdt/ztzl/zxzt/xzgfxwjk/)
- 已核验入口：[涉企行政检查公示专栏](https://nyt.hubei.gov.cn/bmdt/ztzl/zxzt/sqxzjcgszl/)
- 已核验入口：[政策](https://nyt.hubei.gov.cn/zfxxgk/zc_GK2020/gfxwj_GK2020/)
- 已核验入口：[通知](https://nyt.hubei.gov.cn/zfxxgk/zc_GK2020/qtzdgkwj_GK2020/tz/)
- 已核验入口：[公示](https://nyt.hubei.gov.cn/zfxxgk/zc_GK2020/qtzdgkwj_GK2020/gs/)
- 已核验入口：[许可/服务](https://nyt.hubei.gov.cn/zfxxgk/fdzdgknr_GK2020/xkfw_GK2020/)
- 已核验入口：[行政许可结果](https://nyt.hubei.gov.cn/zfxxgk/fdzdgknr_GK2020/xkfw_GK2020/xzxkjg/)
- 已核验入口：[集中采购目录、标准、采购实施情况](https://nyt.hubei.gov.cn/zfxxgk/fdzdgknr_GK2020/zfcg_GK2020/cgssqk_GK2020/)
- 已核验入口：[政策执行及落实情况](https://nyt.hubei.gov.cn/zfxxgk/fdzdgknr_GK2020/qtzdgknr_GK2020/zczxjlsq/)
- 已核验入口：[业务通知](https://nyt.hubei.gov.cn/bmdt/yw/ywtz/)
- 已核验入口：[来信公示](https://nyt.hubei.gov.cn/hdjl/lxgs/lxslfkqktj/)
- 已核验入口：[重要文件](https://nyt.hubei.gov.cn/bmdt/ztzl/zxzt/hbdsctrpc/zywj/)
- 已核验入口：[文件通知](https://nyt.hubei.gov.cn/bmdt/ztzl/zxzt/bwpfxc/wjtz/)
- 已核验入口：[法律法规](https://nyt.hubei.gov.cn/bmdt/ztzl/zxzt/bwpfxc/flfg/)
- 已核验入口：[湖北省高标准农田建设](https://nyt.hubei.gov.cn/bmdt/ztzl/wqzt/hbsgbzntjs/tzgg/)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 04 黑龙江省农业农村厅

- 首页：https://nynct.hlj.gov.cn/
- 浏览器渲染/兜底页面：23。
- 已核验入口：[通知公告](https://nynct.hlj.gov.cn/nynct/c115385/public_list.shtml)
- 已核验入口：[政策解读](https://nynct.hlj.gov.cn/nynct/c115426/zfxxgk.shtml?tab=zcjd)
- 已核验入口：[政策法规](https://nynct.hlj.gov.cn/nynct/c115424/zfxxgk.shtml?tab=zcjd)
- 已核验入口：[政策](https://nynct.hlj.gov.cn/nynct/c115418/zfxxgk.shtml?tab=gkzc)
- 已核验入口：[行政规范性文件](https://nynct.hlj.gov.cn/nynct/c115420/zfxxgk.shtml?tab=gfxwj)
- 已核验入口：[行政规范性文件](https://nynct.hlj.gov.cn/common/search/23cdfed149794ac0be7112079ed129a0?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[其它文件](https://nynct.hlj.gov.cn/common/search/40d47503032d4e4e9ba4673cbb000aa9?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[其它文件子栏目](https://nynct.hlj.gov.cn/common/getChannelList?channelCode=c115421&websiteCodeName=nynct)
- 已核验入口：[政策解读](https://nynct.hlj.gov.cn/common/search/a1929eaf10cc43b9b7fc712dbd8ba74b?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[人事信息](https://nynct.hlj.gov.cn/common/search/ef6d043b230e460f8b47bc0cfc9304fb?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[行政许可子栏目](https://nynct.hlj.gov.cn/common/getChannelList?channelCode=c115465&websiteCodeName=nynct)
- 已核验入口：[政策法规](https://nynct.hlj.gov.cn/common/search/d3c2472c2e114718a6457ba74299cb88?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[支持大豆加工企业发展相关政策汇编](https://nynct.hlj.gov.cn/nynct/c115492/public_list.shtml)
- 已核验入口：[法律法规](https://nynct.hlj.gov.cn/nynct/c115792/public_list.shtml)
- 已核验入口：[政策文件](https://nynct.hlj.gov.cn/nynct/c115793/public_list.shtml)
- 已核验入口：[人事信息](https://nynct.hlj.gov.cn/nynct/c115444/zfxxgk.shtml)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 05 南通市农业农村局

- 首页：https://nyncj.nantong.gov.cn/
- 浏览器渲染/兜底页面：20。
- 已核验入口：[政策解读](https://nyncj.nantong.gov.cn/ntsnwx/zcjd/zcjd.html)
- 已核验入口：[公示公告](https://nyncj.nantong.gov.cn/ntsnwx/gggs/gggs.html)
- 已核验入口：[行政规范性文件](https://nyncj.nantong.gov.cn/ntsnwx/gfxwj2/gfxwj2.html)
- 已核验入口：[政策文件](https://nyncj.nantong.gov.cn/ntsnwx/zcwj/zcwj.html)
- 已核验入口：[涉企行政检查公示](https://nyncj.nantong.gov.cn/ntsnwx/jczt/jczt.html)
- 已核验入口：[人事信息](https://nyncj.nantong.gov.cn/ntsnwx/rsxx2/rsxx2.html)
- 已核验入口：[检查标准](https://nyncj.nantong.gov.cn/ntsnwx/jcbz/jcbz.html)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 06 国家发展和改革委员会

- 首页：https://www.ndrc.gov.cn/
- 浏览器渲染/兜底页面：2。
- 已核验入口：[通知公告](https://www.ndrc.gov.cn/xwdt/tzgg/)
- 已核验入口：[政策](https://www.ndrc.gov.cn/xxgk/)
- 已核验入口：[规范性文件](https://www.ndrc.gov.cn/xxgk/wjk/index.html?tab=gfxwj)
- 已核验入口：[公告](https://www.ndrc.gov.cn/xxgk/wjk/index.html?tab=gg)
- 已核验入口：[通知](https://www.ndrc.gov.cn/xxgk/wjk/index.html?tab=tz)
- 已核验入口：[政策解读](https://www.ndrc.gov.cn/xxgk/wjk/index.html?tab=zcjd)
- 已核验入口：[政策解读](https://cjjjd.ndrc.gov.cn/gongzuodongtai/quanweifabu/zhengcejiedu/)
- 已核验入口：[规划政策](https://www.ndrc.gov.cn/xwdt/ztzl/cjsjyth1/ghzc/)
- 已核验入口：[政策解读](https://www.ndrc.gov.cn/xwdt/ztzl/cjsjyth1/zcjd/)
- 已核验入口：[规划政策](https://www.ndrc.gov.cn/xwdt/ztzl/hnqmshggkf/ghzc/)
- 已核验入口：[规范性文件](https://www.ndrc.gov.cn/xxgk/zcfb/ghxwj/)
- 已核验入口：[公告](https://www.ndrc.gov.cn/xxgk/zcfb/gg/)
- 已核验入口：[通知](https://www.ndrc.gov.cn/xxgk/zcfb/tz/)
- 已核验入口：[政策图解](https://www.ndrc.gov.cn/xxgk/jd/zctj/)
- 已核验入口：[政策](https://www.ndrc.gov.cn/xxgk/zcfb/fzggwl/)
- 已核验入口：[政策解读](https://www.ndrc.gov.cn/xxgk/jd/jd/)
- 已核验入口：[规章](https://zfxxgk.ndrc.gov.cn/web/zclist.jsp?dirid=40&pid=39)
- 已核验入口：[行政规范性文件](https://zfxxgk.ndrc.gov.cn/web/zclist.jsp?dirid=41&pid=39)
- 已核验入口：[人事工作信息](https://zfxxgk.ndrc.gov.cn/web/dirlist.jsp?dirid=31&pid=11)
- 已核验入口：[民营经济政策一点通](https://myjj.ndrc.gov.cn/hqzczd/)
- 已核验入口：[31条及配套文件](https://myjj.ndrc.gov.cn/31file/)
- 已核验入口：[最新政策](https://myjj.ndrc.gov.cn/hqzczd/search.html?tab=0)
- 已核验入口：[政策解读](https://myjj.ndrc.gov.cn/hqzczd/zcjd/)
- 已核验入口：[网上公示及调查](https://www.ndrc.gov.cn/hdjl/wsgsjdc/)
- 已核验入口：[通知](https://jwtz.ndrc.gov.cn/jwtz/newsHeader/findByTypeAndNumberNew?type=tzgg)
- 已核验入口：[公示公告](https://jwtz.ndrc.gov.cn/jwtz/newsHeader/findByTypeAndNumberNew?type=wgts)
- 已核验入口：[政策法规](https://jwtz.ndrc.gov.cn/jwtz/newsHeader/findByTypeAndNumberNew?type=zcfg)
- 已核验入口：[全国投资项目在线审批监管](https://www.ndrc.gov.cn/zwfw/)
- 已核验入口：[发改法规](https://www.ndrc.gov.cn/fggz/fgfg/dfxx/)
- 已核验入口：[投资法规与政策动态](https://www.ndrc.gov.cn/fggz/gdzctz/tzfg/)
- 已核验入口：[政策规划](https://www.ndrc.gov.cn/fggz/zcssfz/zcgh/)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 07 江苏省发展和改革委员会

- 首页：https://fzggw.jiangsu.gov.cn/
- 浏览器渲染/兜底页面：2。
- 已核验入口：[通知公告](https://fzggw.jiangsu.gov.cn/col/col284/index.html)
- 已核验入口：[政策解读](https://fzggw.jiangsu.gov.cn/col/col314/index.html)
- 已核验入口：[网上公示](https://fzggw.jiangsu.gov.cn/col/col319/index.html)
- 已核验入口：[政策文件](https://fzggw.jiangsu.gov.cn/module/jslib/zcjd/zcjd.htm)
- 已核验入口：[信用信息公示专栏](https://fzggw.jiangsu.gov.cn/col/col59371/index.html)
- 已核验入口：[法规规章规范性文件](https://fzggw.jiangsu.gov.cn/col/col59308/index.html)
- 已核验入口：[其他文件](https://fzggw.jiangsu.gov.cn/col/col51012/index.html)
- 已核验入口：[人事工作信息](https://fzggw.jiangsu.gov.cn/col/col51004/index.html)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 08 湖北省发展和改革委员会

- 首页：https://fgw.hubei.gov.cn/
- 浏览器渲染/兜底页面：659。
- 已核验入口：[通知公告](https://fgw.hubei.gov.cn/fbjd/zc/zcwj/)
- 已核验入口：[政策文件](https://fgw.hubei.gov.cn/fbjd/zc/gfwj/)
- 已核验入口：[政策专题](https://fgw.hubei.gov.cn/fgjj/ztzl/zyzl/zcwj/)
- 已核验入口：[审批](https://fgw.hubei.gov.cn/fbjd/xxgkml/zdjsxm/pzjgxx/sp/)
- 已核验入口：[政策说](https://fgw.hubei.gov.cn/fgjj/sjsfg/zc/)
- 已核验入口：[来信公示](https://fgw.hubei.gov.cn/hdjl/lxgs/)
- 已核验入口：[规范性文件](https://fgw.hubei.gov.cn/fbjd/zc/gfwj/h5.shtml)
- 已核验入口：[其他主动公开文件](https://fgw.hubei.gov.cn/fbjd/zc/zcwj/h5.shtml)
- 已核验入口：[政策解读](https://fgw.hubei.gov.cn/fbjd/zc/zcjd/h5.shtml)
- 已核验入口：[行政许可结果](https://fgw.hubei.gov.cn/fbjd/xxgkml/xkfw/xzxkjg/h5.shtml)
- 已核验入口：[审批](https://fgw.hubei.gov.cn/fbjd/xxgkml/zdjsxm/pzjgxx/sp/h5.shtml)
- 已核验入口：[政策执行及落实情况](https://fgw.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/zczx/h5.shtml)
- 已核验入口：[通知公告](https://fgw.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/ywjwj2019n1y16rq/tzgg/h5.shtml)
- 已核验入口：[处室文件](https://fgw.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/ywjwj2019n1y16rq/cswj/h5.shtml)
- 已核验入口：[规范文件](https://fgw.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/ywjwj2019n1y16rq/gfwj_10369/h5.shtml)
- 已核验入口：[政策](https://fgw.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/wj24n2y16r/zc1/h5.shtml)
- 已核验入口：[通知公告](https://fgw.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/wj24n2y16r/tzgg/h5.shtml)
- 已核验入口：[法规处(营商环境建设处)](https://fgw.hubei.gov.cn/fbjd/xxgkml/jgzn/nsjg/fgc/)
- 已核验入口：[人事处](https://fgw.hubei.gov.cn/fbjd/xxgkml/jgzn/nsjg/rsc/)
- 已核验入口：[通知公告](https://fgw.hubei.gov.cn/gzjj/tzgg/)
- 已核验入口：[民生价费政策系列问答](https://fgw.hubei.gov.cn/fgjj/ztzl/zl/2024/msjf/)
- 已核验入口：[政策解读](https://fgw.hubei.gov.cn/fbjd/zc/zcjd/)
- 已核验入口：[行政许可结果](https://fgw.hubei.gov.cn/fbjd/xxgkml/xkfw/xzxkjg/)
- 已核验入口：[政策执行及落实情况](https://fgw.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/zczx/)
- 已核验入口：[原物价文件19年1月16日前](https://fgw.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/ywjwj2019n1y16rq/)
- 已核验入口：[原省公共资源交易监督管理局文件24年2月16日前](https://fgw.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/wj24n2y16r/)
- 已核验入口：[结果公示](https://fgw.hubei.gov.cn/fbjd/xxgkml/zdjsxm/)
- 已核验入口：[项目审批数据集](https://fgw.hubei.gov.cn/fgjj/zwsjkf/sjj/xmsp/)
- 已核验入口：[通知数据集](https://fgw.hubei.gov.cn/fgjj/zwsjkf/sjj/tz/)
- 已核验入口：[项目审批数据接口](https://fgw.hubei.gov.cn/fgjj/zwsjkf/sjjk/xmsp/)
- 已核验入口：[通知](https://fgw.hubei.gov.cn/gzjj/tzgg/wjtz/)
- 已核验入口：[公示](https://fgw.hubei.gov.cn/gzjj/tzgg/wjgs/)
- 已核验入口：[公告](https://fgw.hubei.gov.cn/gzjj/tzgg/wjgg/)
- 已核验入口：[项目建议书审批结果](https://fgw.hubei.gov.cn/fbjd/xxgkml/zdjsxm/pzjgxx/sp/xmjysspjg/)
- 已核验入口：[可行性研究报告审批结果](https://fgw.hubei.gov.cn/fbjd/xxgkml/zdjsxm/pzjgxx/sp/kxxyjbgspjg/)
- 已核验入口：[初步设计文件审批结果](https://fgw.hubei.gov.cn/fbjd/xxgkml/zdjsxm/pzjgxx/sp/cbsjwjspjg/)
- 已核验入口：[项目审批](https://fgw.hubei.gov.cn/fgjj/zwsjkf/sjj/xmsp/index.shtml)
- 已核验入口：[通知](https://fgw.hubei.gov.cn/fgjj/zwsjkf/sjj/tz/index.shtml)
- 已核验入口：[财政部税务总局关于减征部分乘用车车辆购置税的公告](https://fgw.hubei.gov.cn/fgjj/ztzl/zl/2022/hqzchb/index.shtml)
- 已核验入口：[湖北省行政事业性收费标准清单](https://fgw.hubei.gov.cn/fbjd/zc/zcwj/gg/202607/t20260707_5972482.shtml)
- 已核验入口：[相关文件](https://fgw.hubei.gov.cn/bsfw/jyjd/wjxz/)
- 已核验入口：[政策咨询服务电话](https://fgw.hubei.gov.cn/fzlm/fzgn/lxwm/index.shtml)
- 已核验入口：[政策咨询服务电话](https://fgw.hubei.gov.cn/fzlm/fzgn/lxwm/h5.shtml)
- 已核验入口：[政策问答库](https://fgw.hubei.gov.cn/fgjj/ztzl/zl/2021/zsk/)
- 已核验入口：[【征集意见及反馈】关于征求湖北省招标投标负面清单意见的通知](https://fgw.hubei.gov.cn/hdjl/dczj/myzj/yjzjxq.shtml?collectionId=3130&siteId=41&status=1)
- 已核验入口：[【征集意见及反馈】省发改委关于征求定价目录修订意见的通知](https://fgw.hubei.gov.cn/hdjl/dczj/myzj/yjzjxq.shtml?collectionId=1286&siteId=41&status=1)
- 已核验入口：[【公示反馈】全省公共资源交易有关规定清理结果公示结果反馈](https://fgw.hubei.gov.cn/hdjl/dczj/myzj/yjzjxq.shtml?collectionId=597&siteId=41&status=1)
- 已核验入口：[您对“湖北省投资项目联合审批办事大厅”是否满意](https://fgw.hubei.gov.cn/hdjl/dczj/wsdc/wjdc.shtml?/personalCenter/)
- 已核验入口：[关于我委“网上信访”工作实施方案向社会征求意见的公告](https://fgw.hubei.gov.cn/hdjl/dczj/myzj/yjzjxq.shtml?collectionId=552&siteId=41&status=1)
- 已核验入口：[关于《湖北省政府重大投资项目公示试行办法》的意见征集](https://fgw.hubei.gov.cn/hdjl/dczj/myzj/yjzjxq.shtml?collectionId=554&siteId=41&status=1)
- 已核验入口：[结果公示](https://fgw.hubei.gov.cn/bsfw/)
- 已核验入口：[通知公告](https://fgw.hubei.gov.cn/fbjd/xxgkml/jgzn/wgdw/nyj/mtglc/tzgg/)
- 已核验入口：[相关政策](https://fgw.hubei.gov.cn/fgjj/ztzl/zl/2022/zdxm/)
- 已核验入口：[相关政策](https://fgw.hubei.gov.cn/fgjj/ztzl/zl/2023/jgfw/)
- 已核验入口：[政策](https://fgw.hubei.gov.cn/fgjj/ztzl/zl/2023/jgfw/zc_78952/jysf/)
- 已核验入口：[教育收费标准](https://fgw.hubei.gov.cn/fgjj/ztzl/zl/2023/jgfw/sfbz/sf/jysfbz/)
- 已核验入口：[景区收费标准](https://fgw.hubei.gov.cn/fgjj/ztzl/zl/2023/jgfw/sfbz/sf/jqsfbz/202604/t20260430_5926383.shtml)
- 已核验入口：[电价收费标准](https://fgw.hubei.gov.cn/fgjj/ztzl/zl/2023/jgfw/sfbz/sf/djsfbz/)
- 已核验入口：[水价收费标准](https://fgw.hubei.gov.cn/fgjj/ztzl/zl/2023/jgfw/sfbz/sf/sjsfbz/)
- 已核验入口：[油价收费标准](https://fgw.hubei.gov.cn/fgjj/ztzl/zl/2023/jgfw/sfbz/sf/yjsfbz/)
- 已核验入口：[污废收费标准](https://fgw.hubei.gov.cn/fgjj/ztzl/zl/2023/jgfw/sfbz/sf/wfsfbz/)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 09 黑龙江省发展和改革委员会

- 首页：https://drc.hlj.gov.cn/
- 浏览器渲染/兜底页面：12。
- 已核验入口：[公示公告](https://drc.hlj.gov.cn/drc/c111433/common_list.shtml)
- 已核验入口：[政策](https://drc.hlj.gov.cn/drc/c111442/common_zfxxgk_fgw.shtml?tab=gkzc)
- 已核验入口：[政策解读](https://drc.hlj.gov.cn/drc/c111446/common_zfxxgk.shtml?tab=zcjd)
- 已核验入口：[行政规范性文件](https://drc.hlj.gov.cn/drc/c111444/common_zfxxgk_fgw.shtml?tab=gfxwj)
- 已核验入口：[政策解读](https://drc.hlj.gov.cn/drc/c111446/common_zfxxgk_fgw.shtml?tab=zcjd)
- 已核验入口：[行政许可](https://drc.hlj.gov.cn/drc/c111481/common_zfxxgk_fgw.shtml)
- 已核验入口：[行政规范性文件](https://drc.hlj.gov.cn/common/search/48c7342f13234664a532ed86cd8fa5c5?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[其它文件](https://drc.hlj.gov.cn/common/search/9b74f8a4b9274ccca081bd75467d1775?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[政策解读](https://drc.hlj.gov.cn/common/search/d7a06c7eae9546869e9de1578c1776e9?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[行政许可](https://drc.hlj.gov.cn/common/search/b1f58e418456482389c8f9d66adb7b63?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 10 南通市发展和改革委员会

- 首页：https://fgw.nantong.gov.cn/
- 浏览器渲染/兜底页面：21。
- 已核验入口：[政策文件](https://fgw.nantong.gov.cn/ntsfgw/zcwj/zcwj.html)
- 已核验入口：[规范性文件](https://fgw.nantong.gov.cn/ntsfgw/gfxwj/gfxwj.html)
- 已核验入口：[人事信息](https://fgw.nantong.gov.cn/ntsfgw/rsxx/rsxx.html)
- 已核验入口：[政策解读](https://fgw.nantong.gov.cn/ntsfgw/jdhy/jdhy.html)
- 已核验入口：[公告公示](https://fgw.nantong.gov.cn/ntsfgw/gggs/gggs.html)
- 已核验入口：[行政许可](https://fgw.nantong.gov.cn/ntsfgw/xzxk/xzxk.html)
- 已核验入口：[政策解读](https://fgw.nantong.gov.cn/ntsfgw/zcjd/zcjd.html)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 11 中华人民共和国生态环境部

- 首页：https://www.mee.gov.cn/
- 浏览器渲染/兜底页面：19。
- 已核验入口：[公示公告](https://www.mee.gov.cn/ywdt/gsgg/)
- 已核验入口：[中央有关文件](https://www.mee.gov.cn/zcwj/zyygwj/)
- 已核验入口：[国务院有关文件](https://www.mee.gov.cn/zcwj/gwywj/)
- 已核验入口：[部文件](https://www.mee.gov.cn/zcwj/bwj/)
- 已核验入口：[办公厅文件](https://www.mee.gov.cn/zcwj/bgtwj/)
- 已核验入口：[行政审批文件](https://www.mee.gov.cn/zcwj/xzspwj/)
- 已核验入口：[核安全局文件](https://www.mee.gov.cn/zcwj/haqjwj/)
- 已核验入口：[文件库](https://www.mee.gov.cn/wjk/)
- 已核验入口：[规章库](https://www.mee.gov.cn/gzk/)
- 已核验入口：[公告](https://www.mee.gov.cn/zcwj/bwj/gg/)
- 已核验入口：[文件](https://www.mee.gov.cn/zcwj/bwj/wj/)
- 已核验入口：[文件](https://www.mee.gov.cn/zcwj/bgtwj/wj/)
- 已核验入口：[文件](https://www.mee.gov.cn/zcwj/haqjwj/wj/)
- 已核验入口：[法规标准](https://www.mee.gov.cn/ywgz/fgbz/)
- 已核验入口：[政策规划与业务综合](https://www.mee.gov.cn/ywgz/zcghtjdd/)
- 已核验入口：[行政体制与人事](https://www.mee.gov.cn/ywgz/xztzyrs/)
- 已核验入口：[排污许可](https://www.mee.gov.cn/ywgz/pwxkgl/)
- 已核验入口：[政策文件](https://www.mee.gov.cn/zcwj/)
- 已核验入口：[全国排污许可证管理信息平台](https://permit.mee.gov.cn/permitExt/defaults/default-index!getInformation.action)
- 已核验入口：[公示区](https://www.mee.gov.cn/ywdt/gsgg/gongshi/)
- 已核验入口：[公告区](https://www.mee.gov.cn/ywdt/gsgg/tz/)
- 已核验入口：[公示](https://www.mee.gov.cn/ywdt/gsgg/gongshi/gsq/)
- 已核验入口：[往期公示](https://www.mee.gov.cn/ywdt/gsgg/gongshi/wqgs_1/)
- 已核验入口：[党纪法规](https://jjjcz.mee.gov.cn/djfg/)
- 已核验入口：[规范性文件](https://jjjcz.mee.gov.cn/djfg/dnfgzd/gfxwj/)
- 已核验入口：[法律规范性文件](https://jjjcz.mee.gov.cn/djfg/gjflfg/flgfxwj/)
- 已核验入口：[行政法规](https://jjjcz.mee.gov.cn/djfg/gjflfg/xzfg/)
- 已核验入口：[部委规章](https://jjjcz.mee.gov.cn/djfg/gjflfg/bwgz/hjgz/)
- 已核验入口：[法规与标准司](https://www.mee.gov.cn/zjhb/bjg/fgs/)
- 已核验入口：[行政体制与人事司](https://www.mee.gov.cn/zjhb/bjg/rss/)
- 已核验入口：[行政法规](https://www.mee.gov.cn/ywgz/fgbz/xzfg/)
- 已核验入口：[标准](https://www.mee.gov.cn/ywgz/fgbz/bz/)
- 已核验入口：[生态环境政策](https://www.mee.gov.cn/ywgz/zcghtjdd/sthjzc/)
- 已核验入口：[干部人事管理](https://www.mee.gov.cn/ywgz/xztzyrs/rcgl/)
- 已核验入口：[科技规划政策与体制改革](https://www.mee.gov.cn/ywgz/kjycw/sthjkjcx/kjghzcytzgg/)
- 已核验入口：[海洋倾废管理与审批](https://www.mee.gov.cn/ywgz/hysthjbh/hyqfglysp/)
- 已核验入口：[政策法规与标准规范](https://www.mee.gov.cn/ywgz/gtfwyhxpgl/hxphjgl/zcfgybzgf/)
- 已核验入口：[政策](https://www.mee.gov.cn/ywgz/gtfwyhxpgl/gnlygz/zczc/)
- 已核验入口：[管理文件](https://www.mee.gov.cn/ywgz/hjyxpj/qyyghhjyxpj/xgwj/)
- 已核验入口：[拟审查项目公示](https://www.mee.gov.cn/ywgz/hjyxpj/jsxmhjyxpj/nscxmgs/)
- 已核验入口：[已批准项目公告](https://www.mee.gov.cn/ywgz/hjyxpj/jsxmhjyxpj/ypzxmgg/)
- 已核验入口：[政策法规](https://www.mee.gov.cn/ywgz/hjyxpj/jsxmhjyxpj/jszcfg/)
- 已核验入口：[政策文件](https://www.mee.gov.cn/ywgz/hjyxpj/jsxmhjyxbgsbbzjdgl/zcwj/)
- 已核验入口：[有关文件](https://www.mee.gov.cn/ywgz/hjwrjb/ygwj/)
- 已核验入口：[规章](https://www.mee.gov.cn/gzk/gz/)
- 已核验入口：[行政规范性文件](https://www.mee.gov.cn/xxgk2018/xxgk/xzgfxwj/)
- 已核验入口：[生态环境部公告](https://www.mee.gov.cn/xxgk2018/227/228/index_11252.html)
- 已核验入口：[生态环境部文件](https://www.mee.gov.cn/xxgk2018/227/230/index_11252.html)
- 已核验入口：[生态环境部办公厅文件](https://www.mee.gov.cn/xxgk2018/227/232/index_11252.html)
- 已核验入口：[国家核安全局文件](https://www.mee.gov.cn/xxgk2018/227/234/index_11252.html)
- 已核验入口：[环评审批文件](https://www.mee.gov.cn/xxgk2018/227/238/index_11252.html)
- 已核验入口：[环境标准](https://www.mee.gov.cn/xxgk2018/160/191/193/index_6700.html)
- 已核验入口：[人事管理](https://www.mee.gov.cn/xxgk2018/160/195/196/index_6700.html)
- 已核验入口：[法规与标准司](https://www.mee.gov.cn/xxgk2018/203/207/index_6700.html)
- 已核验入口：[行政体制与人事司](https://www.mee.gov.cn/xxgk2018/203/208/index_6700.html)
- 已核验入口：[招标公告](https://www.mee.gov.cn/xxgk/zfcg/zbxx/)
- 已核验入口：[中标公告](https://www.mee.gov.cn/xxgk/zfcg/zbxx09/)
- 已核验入口：[环境保护部公告](https://www.mee.gov.cn/xxgklssj/73/74/index_6709.html)
- 已核验入口：[环境保护部文件](https://www.mee.gov.cn/xxgklssj/73/76/index_6709.html)
- 已核验入口：[环境保护部人事任免文件](https://www.mee.gov.cn/xxgklssj/73/78/index_6709.html)
- 已核验入口：[环境保护部办公厅文件](https://www.mee.gov.cn/xxgklssj/73/79/index_6709.html)
- 已核验入口：[国家核安全局文件](https://www.mee.gov.cn/xxgklssj/73/81/index_6709.html)
- 已核验入口：[环评审批文件](https://www.mee.gov.cn/xxgklssj/73/99/index_6709.html)
- 已核验入口：[环境标准](https://www.mee.gov.cn/xxgklssj/18/47/87/index_6709.html)
- 已核验入口：[人事管理](https://www.mee.gov.cn/xxgklssj/18/58/59/index_6709.html)
- 已核验入口：[政策法规司](https://www.mee.gov.cn/xxgklssj/1/4/index_6709.html)
- 已核验入口：[行政体制与人事司](https://www.mee.gov.cn/xxgklssj/1/5/index_6709.html)
- 已核验入口：[科技标准司](https://www.mee.gov.cn/xxgklssj/1/6/index_6709.html)
- 已核验入口：[政策](https://www.mee.gov.cn/xxgk2018/)
- 已核验入口：[行政规范性文件](https://www.mee.gov.cn/xxgk2018/index_12965.html)
- 已核验入口：[政策例行吹风会](https://www.mee.gov.cn/zcwj/zclcfh/)
- 已核验入口：[政策解读](https://www.mee.gov.cn/zcwj/zcjd/)
- 已核验入口：[中央有关文件](https://nnsa.mee.gov.cn/zcwj/zyygwj/)
- 已核验入口：[国务院有关文件](https://nnsa.mee.gov.cn/zcwj/gwyygwj/)
- 已核验入口：[部文件](https://nnsa.mee.gov.cn/zcwj/bwj/)
- 已核验入口：[核安全局文件](https://nnsa.mee.gov.cn/zcwj/haqjwj/)
- 已核验入口：[文件](https://nnsa.mee.gov.cn/zcwj/haqjwj/wj/)
- 已核验入口：[政策文件](https://nnsa.mee.gov.cn/zcwj/)
- 已核验入口：[公示公告](https://nnsa.mee.gov.cn/ywdt/gsqg/)
- 已核验入口：[通知公告](https://nro.mee.gov.cn/gzdt_14390/tztg/)
- 已核验入口：[许可证信息](https://nro.mee.gov.cn/xkzxx_14421/)
- 已核验入口：[法律法规](https://ecro.mee.gov.cn/fgbz/fl/)
- 已核验入口：[行政法规](https://ecro.mee.gov.cn/fgbz/xzfg/)
- 已核验入口：[部门规章](https://ecro.mee.gov.cn/fgbz/gz/)
- 已核验入口：[通知公告](https://scro.mee.gov.cn/zhxx/tzgg/)
- 已核验入口：[法规标准](https://scro.mee.gov.cn/fgbz/fl/)
- 已核验入口：[行政法规](https://scro.mee.gov.cn/fgbz/xzfg/)
- 已核验入口：[信息公告](https://nero.mee.gov.cn/xxgg/)
- 已核验入口：[政策法规](https://nero.mee.gov.cn/gzfw/zcfg/)
- 已核验入口：[公示公告](https://cjjg.mee.gov.cn/xxgk/tzgg/)
- 已核验入口：[政策法规](https://cjjg.mee.gov.cn/xxgk/zcfg/)
- 已核验入口：[科技标准](https://cjjg.mee.gov.cn/zsyd/kjbz/)
- 已核验入口：[政策文件](https://huanghejg.mee.gov.cn/falvfg/hhlyxgsthjfl/)
- 已核验入口：[生态环境相关法规](https://huanghejg.mee.gov.cn/falvfg/sthjxgfg/)
- 已核验入口：[生态环境部有关文件](https://huanghejg.mee.gov.cn/falvfg/sthjbygwj/)
- 已核验入口：[行政许可](https://hhbhjg.mee.gov.cn/xzxk/hygc/)
- 已核验入口：[行政许可](https://zjnhjg.mee.gov.cn/zwfw/pwksz/)
- 已核验入口：[行政审批](https://sljg.mee.gov.cn/csxzsp/pwksz/)
- 已核验入口：[行政许可](https://thdhjg.mee.gov.cn/xzxk/hygc/)
- 已核验入口：[通知公告](https://thdhjg.mee.gov.cn/tzgg/)
- 已核验入口：[许可信息公开](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!licenseInformation.action)
- 已核验入口：[许可注销公告](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!xkgg_zxggList.action)
- 已核验入口：[许可撤销公告](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!xkgg_cxggList.action)
- 已核验入口：[许可遗失声明](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!xkgg_yssmList.action)
- 已核验入口：[重要通知](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!xkgg_zytzList.action)
- 已核验入口：[法规标准](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!lawsStandard.action)
- 已核验入口：[关于调整2024年排污许可证年度执行报告报送时间的公告](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!getNewsDetail.action?pkid=a4bb5667-385b-42a4-9f46-4d2d92b3ca86&type=ZYTZ)
- 已核验入口：[全国排污许可证管理信息平台更新通知](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!getNewsDetail.action?pkid=4e9b17bb-1f5d-4833-a4ea-817f23437f82&type=ZYTZ)
- 已核验入口：[关于调整2023年度排污许可证执行报告报送时间的通知](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!getNewsDetail.action?pkid=7152da31-9782-4188-b9dd-adbbb71442d5&type=ZYTZ)
- 已核验入口：[全国排污许可证管理信息平台优化工业噪声管理模块相关功能](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!getNewsDetail.action?pkid=d83fbbbf-9a22-4ec0-8c4b-41c7337fd0af&type=ZYTZ)
- 已核验入口：[全国排污许可证管理信息平台优化固体废物管理模块相关功能](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!getNewsDetail.action?pkid=5efc92a3-2abc-40bd-97b6-de9c008e3ee7&type=ZYTZ)
- 已核验入口：[执行报告优化通知](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!getNewsDetail.action?pkid=a28ad712-e4dc-4cac-9530-c988a984f2c8&type=ZYTZ)
- 已核验入口：[全国排污许可证管理信息平台更新通知（2021年4月23日）](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!getNewsDetail.action?pkid=1cb074b5-6725-40ac-b951-73a94f9f469f&type=ZYTZ)
- 已核验入口：[全国排污许可证管理信息平台更新通知（2021年3月19日）](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!getNewsDetail.action?pkid=d2b6420d-8cbb-4c00-acc8-8af42f52e93f&type=ZYTZ)
- 已核验入口：[全国排污许可证管理信息平台更新通知（2021年1月12日）](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!getNewsDetail.action?pkid=b0f7918b-d3f8-4560-b255-fceb5ff3a8a0&type=ZYTZ)
- 已核验入口：[全国排污许可证管理信息平台更新通知（2020年9月3日）](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!getNewsDetail.action?pkid=e615e70b-79f5-41fc-956f-6d15279c6d27&type=ZYTZ)
- 已核验入口：[全国排污许可证管理信息平台更新通知（2020年8月21日）](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!getNewsDetail.action?pkid=f24bdda0-8cd9-4d82-892a-3eb9c75c6b58&type=ZYTZ)
- 已核验入口：[全国排污许可证管理信息平台更新通知(2020年7月1日)](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!getNewsDetail.action?pkid=a32fbf20-dcd7-4c5b-8379-916d791cc8e4&type=ZYTZ)
- 已核验入口：[平台问题咨询等通知](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!getNewsDetail.action?pkid=e93c0179-c17b-4ff7-979c-35ca841e0e44&type=ZYTZ)
- 已核验入口：[货运港口、水处理通用工序等9行业排污许可证可正式申报](https://permit.mee.gov.cn/perxxgkinfo/syssb/xkgg/xkgg!getNewsDetail.action?pkid=06094231-45fe-41b8-9a52-3487c33a073b&type=ZYTZ)
- 已核验入口：[排污许可管理办法](https://permit.mee.gov.cn/perxxgkinfo/outside/news_detail.jsp?pkid=86ee831b-08b9-48dc-8673-cccaf39574cd&type=Law)
- 已核验入口：[排污许可管理条例（中华人民共和国国务院令第736号）](https://permit.mee.gov.cn/perxxgkinfo/outside/news_detail.jsp?pkid=e3bd81d4-b8e2-4658-9c02-adadf750c907&type=Law)
- 已核验入口：[排污许可管理办法（试行）](https://permit.mee.gov.cn/perxxgkinfo/outside/news_detail.jsp?pkid=17a5acc5-a148-4f08-a37a-444b14492ece&type=Law)
- 已核验入口：[排污许可证管理暂行规定](https://permit.mee.gov.cn/perxxgkinfo/outside/news_detail.jsp?pkid=6943fef8-0aee-4997-98cc-33aaf6e27ba4&type=Law)
- 已核验入口：[国务院办公厅关于印发控制污染物排放许可制实施方案的通知](https://permit.mee.gov.cn/perxxgkinfo/outside/news_detail.jsp?pkid=10ff6ea4-b9b7-402c-9596-89c5f3c1c249&type=Law)
- 已核验入口：[锅炉大气污染物排放标准GB13271-2014](https://permit.mee.gov.cn/perxxgkinfo/outside/news_detail.jsp?pkid=f45dfebd-4c0f-439e-8e35-be195c90beaa&type=SSHYPFBZ)
- 已核验入口：[关于执行大气污染物特别排放限值的公告](https://permit.mee.gov.cn/perxxgkinfo/outside/news_detail.jsp?pkid=b1f2a6ab-69d5-4e31-8b0d-ab0a97316051&type=SSHYPFBZ)
- 已核验入口：[火电厂大气污染物排放标准GB13223-2011](https://permit.mee.gov.cn/perxxgkinfo/outside/news_detail.jsp?pkid=89c9a94e-0293-472c-a1d0-89b5e3322771&type=SSHYPFBZ)
- 已核验入口：[制浆造纸工业水污染物排放标准GB3544-2008](https://permit.mee.gov.cn/perxxgkinfo/outside/news_detail.jsp?pkid=3af76a84-5b5c-4b6f-9f32-7da3dd62cd83&type=SSHYPFBZ)
- 已核验入口：[排污许可证质量核查技术规范](https://permit.mee.gov.cn/perxxgkinfo/outside/news_detail.jsp?pkid=a4ffae63-191f-4716-adc0-ade07f72adca&type=XKJSGF)
- 已核验入口：[排污许可证申请与核发技术规范工业固体废物（试行）](https://permit.mee.gov.cn/perxxgkinfo/outside/news_detail.jsp?pkid=91eb0296-24c7-483b-bbf0-7a533c9f99fb&type=XKJSGF)
- 已核验入口：[排污许可证申请与核发技术规范稀有稀土金属冶炼](https://permit.mee.gov.cn/perxxgkinfo/outside/news_detail.jsp?pkid=b6d1a751-13c6-4cde-9f86-5dd130944d22&type=XKJSGF)
- 已核验入口：[排污许可证申请与核发技术规范工业炉窑](https://permit.mee.gov.cn/perxxgkinfo/outside/news_detail.jsp?pkid=9857fa9c-46e0-4326-b535-d36ccbd62356&type=XKJSGF)
- 已核验入口：[政策规划](https://www.mee.gov.cn/ywgz/fgbz/hjyjk/zcgh/)
- 已核验入口：[技术文件](https://www.mee.gov.cn/ywgz/fgbz/hjyjk/jswj/)
- 已核验入口：[政策规划](https://www.mee.gov.cn/ywgz/fgbz/hjjzgl/zcgh/)
- 已核验入口：[技术文件](https://www.mee.gov.cn/ywgz/fgbz/hjjzgl/jswj/)
- 已核验入口：[通报公告](https://huanghejg.mee.gov.cn/zfxxgk/tzgg/)
- 已核验入口：[行政许可](https://huanghejg.mee.gov.cn/zfxxgk/xkjd/)
- 已核验入口：[通知公告](https://huaihejg.mee.gov.cn/tzgg/)
- 已核验入口：[行政许可](https://huaihejg.mee.gov.cn/xzxk/)
- 已核验入口：[通知公告](https://zjnhjg.mee.gov.cn/tzgg/)
- 已核验入口：[政策法规](https://www.mee.gov.cn/ywgz/pwxkgl/ygzc/)
- 待复核：[页面](https://www.mee.gov.cn/ywgz/kjycw/fphdkzy/)；浏览器仍未通过站点访问校验: https://www.mee.gov.cn/ywgz/kjycw/fphdkzy/

### 12 江苏省生态环境厅

- 首页：https://sthjt.jiangsu.gov.cn/
- 浏览器渲染/兜底页面：1。
- 已核验入口：[通知](https://sthjt.jiangsu.gov.cn/col/col83843/index.html)
- 已核验入口：[公告公示](https://sthjt.jiangsu.gov.cn/col/col83844/index.html)
- 已核验入口：[政策解读](https://sthjt.jiangsu.gov.cn/col/col89449/index.html)
- 已核验入口：[生态环境惠企政策](https://sthjt.jiangsu.gov.cn/col/col87058/index.html)
- 已核验入口：[行政规范性文件](https://sthjt.jiangsu.gov.cn/col/col89427/index.html)
- 已核验入口：[政策文件](https://sthjt.jiangsu.gov.cn/col/col89481/index.html)
- 已核验入口：[行政审批](https://sthjt.jiangsu.gov.cn/col/col83551/index.html)
- 已核验入口：[审批事项清单](https://sthjt.jiangsu.gov.cn/col/col83567/index.html)
- 已核验入口：[危废审批](https://sthjt.jiangsu.gov.cn/col/col83569/index.html)
- 已核验入口：[辐射审批](https://sthjt.jiangsu.gov.cn/col/col83571/index.html)
- 已核验入口：[法规标准](https://sthjt.jiangsu.gov.cn/col/col83553/index.html)
- 已核验入口：[法律法规规章](https://sthjt.jiangsu.gov.cn/col/col83738/index.html)
- 已核验入口：[生态环境标准](https://sthjt.jiangsu.gov.cn/col/col83739/index.html)
- 已核验入口：[涉企行政检查公示](https://sthjt.jiangsu.gov.cn/col/col91972/index.html)
- 已核验入口：[人事教育](https://sthjt.jiangsu.gov.cn/col/col83562/index.html)
- 已核验入口：[人事管理](https://sthjt.jiangsu.gov.cn/col/col83597/index.html)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 13 湖北省生态环境厅

- 首页：https://sthjt.hubei.gov.cn/
- 浏览器渲染/兜底页面：453。
- 已核验入口：[生态环境国家法律法规](https://sthjt.hubei.gov.cn/fbjd/xxgkml/gysyjs/sthj/sthjfg/gjflfg/)
- 已核验入口：[生态环境地方性法规规章](https://sthjt.hubei.gov.cn/fbjd/xxgkml/gysyjs/sthj/sthjfg/flfg/)
- 已核验入口：[行政许可结果](https://sthjt.hubei.gov.cn/fbjd/xxgkml/xkfw/xzxkjg/)
- 已核验入口：[人事信息](https://sthjt.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/gbrsgl/)
- 已核验入口：[生态环境标准](https://sthjt.hubei.gov.cn/fbjd/xxgkml/gysyjs/sthj/hjbz/)
- 已核验入口：[环境保护标准信息查询](https://sthjt.hubei.gov.cn/hjsj/hbbz/)
- 已核验入口：[政策文件](https://sthjt.hubei.gov.cn/fbjd/zc/zcwj/)
- 已核验入口：[政策解读](https://sthjt.hubei.gov.cn/fbjd/zc/zcjd/)
- 已核验入口：[公示中心](https://sthjt.hubei.gov.cn/bsfw/gszx/)
- 已核验入口：[放射源转让审批](https://sthjt.hubei.gov.cn/bsfw/rhfw/fsyzr/)
- 已核验入口：[规范性文件](https://sthjt.hubei.gov.cn/fbjd/zc/gfxwj/)
- 已核验入口：[辐射类建设项目环评批复及许可公告](https://sthjt.hubei.gov.cn/fbjd/xxgkml/gysyjs/sthj/hyfsjg/fshp/)
- 已核验入口：[政策执行及落实情况](https://sthjt.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/zczx/)
- 已核验入口：[建设项目环评审批](https://sthjt.hubei.gov.cn/hjsj/ztzl/jsxmhp/jsxmhpsp/flfg/)
- 已核验入口：[政策文件](https://sthjt.hubei.gov.cn/hjsj/ztzl/jsxmhp/jsxmhpsp/zcwj/gjctxgzcwj/)
- 已核验入口：[省级政策](https://sthjt.hubei.gov.cn/hjsj/ztzl/jsxmhp/jsxmhpsp/zcwj/sjctxgzcwj/)
- 已核验入口：[排污许可](https://sthjt.hubei.gov.cn/hjsj/ztzl/jsxmhp/pwxk/flfg/)
- 已核验入口：[政策文件](https://sthjt.hubei.gov.cn/hjsj/ztzl/jsxmhp/pwxk/zcwj/gjctxgzcwj/)
- 已核验入口：[省级政策](https://sthjt.hubei.gov.cn/hjsj/ztzl/jsxmhp/pwxk/zcwj/sjctxgzcwj/)
- 已核验入口：[水环境保护标准](https://sthjt.hubei.gov.cn/hjsj/hbbz/?itemid=6681)
- 已核验入口：[大气环境保护标准](https://sthjt.hubei.gov.cn/hjsj/hbbz/?itemid=6667)
- 已核验入口：[环境噪声与振动标准](https://sthjt.hubei.gov.cn/hjsj/hbbz/?itemid=6659)
- 已核验入口：[土壤环境保护标准](https://sthjt.hubei.gov.cn/hjsj/hbbz/?itemid=6652)
- 已核验入口：[固体废物环境标准](https://sthjt.hubei.gov.cn/hjsj/hbbz/?itemid=6639)
- 已核验入口：[核辐射与电磁辐射环境保护标准](https://sthjt.hubei.gov.cn/hjsj/hbbz/?itemid=6627)
- 已核验入口：[生态环境保护标准](https://sthjt.hubei.gov.cn/hjsj/hbbz/?itemid=6621)
- 已核验入口：[其他环境保护标准](https://sthjt.hubei.gov.cn/hjsj/hbbz/?itemid=6600)
- 已核验入口：[环评批复文件](https://sthjt.hubei.gov.cn/hjsj/ztzl/jsxmhp/jsxmhpsp/jsxmhppfgk/)
- 已核验入口：[涉企行政检查公示专栏](https://sthjt.hubei.gov.cn/hjsj/ztzl/xzjcgs/index.shtml)
- 已核验入口：[建设项目环评审批与排污许可](https://sthjt.hubei.gov.cn/hjsj/ztzl/jsxmhp/)
- 已核验入口：[地表水环境状况公告](https://sthjt.hubei.gov.cn/fbjd/xxgkml/gysyjs/sthj/hjzl/dbsh/)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 14 黑龙江省生态环境厅

- 首页：http://sthj.hlj.gov.cn/
- 浏览器渲染/兜底页面：28。
- 已核验入口：[通知公告](http://sthj.hlj.gov.cn/sthj/c111952/public_list.shtml)
- 已核验入口：[政策解读](http://sthj.hlj.gov.cn/sthj/c111964/public_zfxxgk.shtml?tab=zcjd)
- 已核验入口：[政策](http://sthj.hlj.gov.cn/sthj/c111958/public_zfxxgk.shtml?tab=gkzc)
- 已核验入口：[行政规范性文件](http://sthj.hlj.gov.cn/sthj/c111960/public_zfxxgk.shtml?tab=gfxwj)
- 已核验入口：[行政执法公示](http://sthj.hlj.gov.cn/sthj/c112109/public_list.shtml)
- 已核验入口：[行政规范性文件](http://sthj.hlj.gov.cn/common/search/f8069a8aefe7444d9796a319d735d9a7?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[政策解读](http://sthj.hlj.gov.cn/common/search/520998ad28c3494c9b49817ad5823bce?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[环境标准](http://sthj.hlj.gov.cn/common/search/bd53a5b775524b90aeae57833320aded?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[人事信息](http://sthj.hlj.gov.cn/common/search/8f379979ce1949d48480091782208b69?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[人事信息子栏目](http://sthj.hlj.gov.cn/common/getChannelList?channelCode=c111978&websiteCodeName=sthj)
- 已核验入口：[指导文件](http://sthj.hlj.gov.cn/sthj/c112079/public_list.shtml)
- 已核验入口：[干部任免](http://sthj.hlj.gov.cn/common/search/ef5f8769a34f411fa780793634aa4994?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[环境标准](http://sthj.hlj.gov.cn/sthj/c112016/public_zfxxgk.shtml)
- 已核验入口：[人事信息](http://sthj.hlj.gov.cn/sthj/c111978/public_zfxxgk.shtml)
- 已核验入口：[检查标准](http://sthj.hlj.gov.cn/sthj/c113194/public_list.shtml)
- 待复核：[页面](http://sthj.hlj.gov.cn/sthj/c112028/public_list.shtml)；Page.goto: net::ERR_CERT_DATE_INVALID at https://sthj.hlj.gov.cn/sthj/c112028/public_list.shtml Call log:   - navigating to "https://sthj.hlj.gov.cn/sthj/c112028/public_list.shtml", waiting until "domcontentloaded" 
- 待复核：[页面](http://sthj.hlj.gov.cn/sthj/c112162/jump1.shtml)；Page.goto: net::ERR_CERT_DATE_INVALID at https://sthj.hlj.gov.cn/sthj/c112162/jump1.shtml Call log:   - navigating to "https://sthj.hlj.gov.cn/sthj/c112162/jump1.shtml", waiting until "domcontentloaded" 

### 15 南通市生态环境局

- 首页：https://sthjj.nantong.gov.cn/
- 浏览器渲染/兜底页面：29。
- 已核验入口：[政策文件](https://sthjj.nantong.gov.cn/ntshbj/zcwj/zcwj.html)
- 已核验入口：[政策解读](https://sthjj.nantong.gov.cn/ntshbj/zcjd/zcjd.html)
- 已核验入口：[人事信息](https://sthjj.nantong.gov.cn/ntshbj/rsxx/rsxx.html)
- 已核验入口：[公告公示](https://sthjj.nantong.gov.cn/ntshbj/gggs/gggs.html)
- 已核验入口：[规章及规范性文件](https://sthjj.nantong.gov.cn/ntshbj/gzjgfxwj/gzjgfxwj.html)
- 已核验入口：[涉企行政检查公示](https://sthjj.nantong.gov.cn/ntshbj/sqxzjcgs/sqxzjcgs.html)
- 已核验入口：[公开标准](https://sthjj.nantong.gov.cn/ntshbj/bmwj/bmwj.html)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 16 中华人民共和国应急管理部

- 首页：https://www.mem.gov.cn/
- 浏览器渲染/兜底页面：20。
- 已核验入口：[通知公告](https://www.mem.gov.cn/gk/tzgg/)
- 已核验入口：[政策解读](https://www.mem.gov.cn/gk/zcjd/)
- 已核验入口：[人事信息](https://www.mem.gov.cn/gk/rsxx/)
- 已核验入口：[原国家安全监管总局文件](https://www.mem.gov.cn/gk/gwgg/)
- 已核验入口：[法律法规标准](https://www.mem.gov.cn/fw/flfgbz/fg/)
- 已核验入口：[应急管理部行政许可](https://www.mem.gov.cn/fw/yajzjxzxk/)
- 已核验入口：[行政执法公示](https://www.mem.gov.cn/fw/xzzfgs/)
- 已核验入口：[公文公告](https://www.mem.gov.cn/dj/gwgg/)
- 已核验入口：[规章制度](https://www.mem.gov.cn/dj/gzzd/)
- 已核验入口：[许可事项办理结果](https://www.mem.gov.cn/fw/yajzjxzxk/zjxzxksxbljg/index.shtml)
- 已核验入口：[人事司（党委组织部）](https://www.mem.gov.cn/jg/nsjg/rss/202403/t20240325_400320.shtml)
- 已核验入口：[政策法规司](https://www.mem.gov.cn/jg/nsjg/zcfgs/202403/t20240325_400334.shtml)
- 已核验入口：[公告](https://www.mem.gov.cn/gk/tzgg/yjbgg/)
- 已核验入口：[通知](https://www.mem.gov.cn/gk/tzgg/tz/)
- 已核验入口：[通知](https://www.mem.gov.cn/gk/gwgg/agwzlfl/tz_01/)
- 已核验入口：[公告](https://www.mem.gov.cn/gk/gwgg/agwzlfl/gg_01/)
- 已核验入口：[安全监管总局煤矿安监局公告](https://www.mem.gov.cn/gk/gwgg/agwzlfl/zjmjjgg/)
- 已核验入口：[规范性文件](https://www.mem.gov.cn/gk/gwgg/agwzlfl/gfxwj/)
- 已核验入口：[规章](https://www.mem.gov.cn/fw/flfgbz/gz/)
- 已核验入口：[标准](https://www.mem.gov.cn/fw/flfgbz/bz/bzgg/)
- 已核验入口：[规范性文件](https://www.mem.gov.cn/fw/flfgbz/gfxwj/)
- 已核验入口：[规章](https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/)
- 已核验入口：[安全生产许可类](https://www.mem.gov.cn/fw/yajzjxzxk/aqscxkl/hysytrqqyaqscxk/202008/t20200820_361461.shtml)
- 已核验入口：[行政法规](https://www.mem.gov.cn/fw/flfgbz/fg/xzfg_6144/)
- 已核验入口：[标准文本](https://www.mem.gov.cn/fw/flfgbz/bz/bzwb/)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 17 江苏省应急管理厅

- 首页：https://yjglt.jiangsu.gov.cn/
- 浏览器渲染/兜底页面：3。
- 已核验入口：[通知公告](https://yjglt.jiangsu.gov.cn/col/col3154/index.html)
- 已核验入口：[政策解读](https://yjglt.jiangsu.gov.cn/col/col81373/index.html?number=)
- 已核验入口：[安全生产经济政策专栏](https://yjglt.jiangsu.gov.cn/col/col92901/index.html)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 18 湖北省应急管理厅

- 首页：https://yjt.hubei.gov.cn/
- 浏览器渲染/兜底页面：316。
- 已核验入口：[通知公告](https://yjt.hubei.gov.cn/fbjd/zc/zcfg/)
- 已核验入口：[政策文件](https://yjt.hubei.gov.cn/fbjd/zc/gfwj/)
- 已核验入口：[政策解读](https://yjt.hubei.gov.cn/fbjd/zc/zcjd/)
- 已核验入口：[来信公示](https://yjt.hubei.gov.cn/hdjl/lxgs/)
- 已核验入口：[行政许可结果](https://yjt.hubei.gov.cn/fbjd/xxgkml/xkfw/xzxkgs/)
- 已核验入口：[政策执行及落实情况](https://yjt.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/zczx/)
- 已核验入口：[技术标准](https://yjt.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/jsbz/)
- 已核验入口：[安全生产许可证注销公告](https://yjt.hubei.gov.cn/fbjd/tzgg/wwh/t_5631521.shtml)
- 已核验入口：[安全生产许可证注销公告](https://yjt.hubei.gov.cn/fbjd/tzgg/wwh/t_5462834.shtml)
- 已核验入口：[湖北省应急管理厅关于2023年度行政规范性文件清理结果的公告](https://yjt.hubei.gov.cn/fbjd/zc/gfwj/t_5544641.shtml)
- 已核验入口：[通知公告](https://yjt.hubei.gov.cn/fbjd/tzgg/)
- 已核验入口：[安全生产许可证查询](https://yjt.hubei.gov.cn/bsfw/bmcxfw/xxcx/aqscxk/)
- 已核验入口：[二级安全生产标准化评审机构名单](https://yjt.hubei.gov.cn/bsfw/bmcxfw/xxcx/ejaqsc/202608/t20260803_5988135.shtml)
- 已核验入口：[二级安全生产标准化企业名单](https://yjt.hubei.gov.cn/bsfw/bmcxfw/xxcx/ejanscbz/)
- 已核验入口：[政策问答](https://yjt.hubei.gov.cn/yjgl/ztzl/zcwdpt/index.shtml)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 19 黑龙江省应急管理厅

- 首页：https://yjgl.hlj.gov.cn/
- 浏览器渲染/兜底页面：36。
- 已核验入口：[通知公告](https://yjgl.hlj.gov.cn/yjgl/c104045/list.shtml)
- 已核验入口：[行政规范性文件](https://yjgl.hlj.gov.cn/yjgl/c104069/zfxxgk.shtml?tab=gfxwj)
- 已核验入口：[政策](https://yjgl.hlj.gov.cn/yjgl/c104059/zfxxgk.shtml?tab=gkzc)
- 已核验入口：[政策解读](https://yjgl.hlj.gov.cn/yjgl/c104071/zfxxgk.shtml?tab=zcjd)
- 已核验入口：[规章](https://yjgl.hlj.gov.cn/yjgl/c104060/zfxxgk.shtml?tab=gkzc)
- 已核验入口：[其他文件](https://yjgl.hlj.gov.cn/yjgl/c104070/zfxxgk.shtml?tab=qtwj)
- 已核验入口：[法律规章](https://yjgl.hlj.gov.cn/common/search/417939fe60ce4ac68e806a2e63f9559a?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[法律规章子栏目](https://yjgl.hlj.gov.cn/common/getChannelList?channelCode=c104060&websiteCodeName=yjgl)
- 已核验入口：[行政规范性文件](https://yjgl.hlj.gov.cn/common/search/c3d1320d5ab44c758323ec8adddba612?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[其他文件](https://yjgl.hlj.gov.cn/common/search/8068dfb7d6f04a4885516f4727ac4f5c?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[政策解读](https://yjgl.hlj.gov.cn/common/search/a867e95a71f44bd393efed3260d3acd5?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[行政许可](https://yjgl.hlj.gov.cn/common/search/f3203f17b3354fa6b3a5f99edb6cb1a6?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[行政许可子栏目](https://yjgl.hlj.gov.cn/common/getChannelList?channelCode=c104105&websiteCodeName=yjgl)
- 已核验入口：[安全生产许可](https://yjgl.hlj.gov.cn/common/search/b1ef93ede008476290212c618dadcba3?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[安全生产法律法规](https://yjgl.hlj.gov.cn/common/search/01c96a6e9e6c474894f488bf53ca993c?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[森林草原防火法律法规](https://yjgl.hlj.gov.cn/common/search/3a3f3a9ac7b34af295861597c93b3ae6?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[自然灾害防治法律法规](https://yjgl.hlj.gov.cn/common/search/b19bc950ac344cc19118b6cb82811f0a?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[灾害救援救助法律法规](https://yjgl.hlj.gov.cn/common/search/8fadb02a1f2f44dd812e1fe8920f7a65?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[消防法律法规](https://yjgl.hlj.gov.cn/common/search/fb2e76ae14b147c3a0611119e2ff74f8?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[地方标准](https://yjgl.hlj.gov.cn/common/search/ebd020a161a24236b45781f3e9f63058?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 20 南通市应急管理局

- 首页：https://yjgl.nantong.gov.cn/
- 浏览器渲染/兜底页面：22。
- 已核验入口：[政策解读](https://yjgl.nantong.gov.cn/ntaj/zcjd/zcjd.html)
- 已核验入口：[规章及规范性文件](https://yjgl.nantong.gov.cn/ntaj/gzjgfxwj/gzjgfxwj.html)
- 已核验入口：[政策文件](https://yjgl.nantong.gov.cn/ntaj/zcwj/zcwj.html)
- 已核验入口：[公告公示](https://yjgl.nantong.gov.cn/ntaj/gggs/gggs.html)
- 已核验入口：[涉企行政检查公示](https://yjgl.nantong.gov.cn/ntaj/sqxzjcgs/sqxzjcgs.html)
- 已核验入口：[人事信息](https://yjgl.nantong.gov.cn/ntaj/rsxx/rsxx.html)
- 已核验入口：[检查标准](https://yjgl.nantong.gov.cn/ntaj/jcbz/jcbz.html)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 21 中华人民共和国工业和信息化部

- 首页：https://www.miit.gov.cn/
- 浏览器渲染/兜底页面：159。
- 已核验入口：[最新政策](https://www.miit.gov.cn/xwfb/zxzc/index.html)
- 已核验入口：[政策文件](https://www.miit.gov.cn/search/zcwjk.html?websiteid=110000000000000&pg=&p=&tpl=14&category=183&q=)
- 已核验入口：[政策解读](https://www.miit.gov.cn/zwgk/zcjd/index.html)
- 已核验入口：[文件公示](https://www.miit.gov.cn/zwgk/wjgs/index.html)
- 已核验入口：[部门规章库](https://www.miit.gov.cn/search/bmgzk.html?websiteid=110000000000000&pg=&p=&tpl=14&category=181&q=)
- 已核验入口：[行政规范性文件库](https://www.miit.gov.cn/zc/wjxzfl/xzgfxwj/index.html)
- 已核验入口：[国务院政策例行吹风会](https://www.miit.gov.cn/xwfb/xwfbh/gwyzclxcfh/index.html)
- 已核验入口：[法律法规](https://www.miit.gov.cn/zwgk/zcwj/flfg/index.html)
- 已核验入口：[政策](https://www.miit.gov.cn/zc/wjxzfl/flfg/index.html)
- 已核验入口：[部门规章](https://www.miit.gov.cn/zc/wjxzfl/bmgz/index.html)
- 已核验入口：[工业和信息化部行政执法信息公示平台](https://www.miit.gov.cn/xzzfxxgspt/index.html)
- 已核验入口：[人事任免](https://www.miit.gov.cn/zwgk/rsxx/rsrm/index.html)
- 已核验入口：[文件发布](https://www.miit.gov.cn/jgsj/aqs/wjfb/index.html)
- 已核验入口：[公告](https://www.miit.gov.cn/zwgk/zcwj/wjfb/gg/index.html)
- 已核验入口：[通知](https://www.miit.gov.cn/zwgk/zcwj/wjfb/tz/index.html)
- 已核验入口：[文件发布](https://www.miit.gov.cn/jgsj/kjs/wjfb/index.html)
- 已核验入口：[政策法规](https://www.miit.gov.cn/zcfg/index.html)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 22 江苏省工业和信息化厅

- 首页：https://gxt.jiangsu.gov.cn/
- 浏览器渲染/兜底页面：6。
- 已核验入口：[文件通知](https://gxt.jiangsu.gov.cn/col/col6278/index.html)
- 已核验入口：[公告公示](https://gxt.jiangsu.gov.cn/col/col6281/index.html)
- 已核验入口：[政策文件](https://gxt.jiangsu.gov.cn/col/col80179/index.html)
- 已核验入口：[行政许可与行政处罚双公示](https://gxt.jiangsu.gov.cn/col/col75858/index.html)
- 已核验入口：[江苏省涉企行政检查公示专栏](https://gxt.jiangsu.gov.cn/col/col92051/index.html)
- 已核验入口：[政策文件](https://gxt.jiangsu.gov.cn/col/col6279/index.html)
- 已核验入口：[政策解读](https://gxt.jiangsu.gov.cn/col/col6197/index.html)
- 已核验入口：[政策咨询](https://gxt.jiangsu.gov.cn/jact/front/main.do?sysid=117)
- 已核验入口：[法规规章](https://gxt.jiangsu.gov.cn/col/col64290/index.html)
- 已核验入口：[规范性文件](https://gxt.jiangsu.gov.cn/col/col64776/index.html)
- 已核验入口：[政策文件](https://gxt.jiangsu.gov.cn/col/col89736/index.html)
- 已核验入口：[人事任免](https://gxt.jiangsu.gov.cn/col/col80189/index.html)
- 已核验入口：[行政许可](https://gxt.jiangsu.gov.cn/col/col75859/index.html)
- 已核验入口：[双公示目录清单](https://gxt.jiangsu.gov.cn/col/col80237/index.html)
- 已核验入口：[检查标准](https://gxt.jiangsu.gov.cn/col/col92055/index.html)
- 已核验入口：[省级政策](https://gxt.jiangsu.gov.cn/col/col83658/index.html)
- 已核验入口：[政策文件](https://gxt.jiangsu.gov.cn/col/col91356/index.html)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 23 湖北省经济和信息化厅

- 首页：https://jxt.hubei.gov.cn/
- 浏览器渲染/兜底页面：8。
- 已核验入口：[政策问答知识库](https://jxt.hubei.gov.cn/bmdt/ztzl/zcwdzsk/)
- 已核验入口：[规范性文件](https://jxt.hubei.gov.cn/fbjd/zc/gfxwj/)
- 已核验入口：[政策解读](https://jxt.hubei.gov.cn/fbjd/zc/zcjd/)
- 已核验入口：[通知公告](https://jxt.hubei.gov.cn/fbjd/zc/qtzdgkwj/gwfb/)
- 已核验入口：[政策简编](https://jxt.hubei.gov.cn/fzlm/zcjb/)
- 已核验入口：[惠企政策](https://jxt.hubei.gov.cn/wzlm/hqzc/)
- 已核验入口：[来信公示](https://jxt.hubei.gov.cn/hdjl/lxgs/)
- 已核验入口：[惠企政策](https://jxt.hubei.gov.cn/fzlm/znwd/index.shtml?tzwt=%E6%83%A0%E4%BC%81%E6%94%BF%E7%AD%96)
- 已核验入口：[政策文件](https://jxt.hubei.gov.cn/fbjd/zc/gfxwj/indexzzms.shtml)
- 已核验入口：[公示公告](https://jxt.hubei.gov.cn/fbjd/zc/qtzdgkwj/gsgg/)
- 已核验入口：[政策法规处](http://jxt.hubei.gov.cn/fbjd/xxgkml/jgzn/nsjg/zcfgc/gzzz/201912/t20191231_1822366.shtml)
- 已核验入口：[产业政策处](http://jxt.hubei.gov.cn/fbjd/xxgkml/jgzn/nsjg/cyzcc/gzzz/201912/t20191231_1822534.shtml)
- 已核验入口：[人事处](http://jxt.hubei.gov.cn/fbjd/xxgkml/jgzn/nsjg/rsc/gzzz/202003/t20200325_2190714.shtml)
- 已核验入口：[湖北省化肥农药发展中心](http://jxt.hubei.gov.cn/fbjd/xxgkml/jgzn/zsdw/hfnyfzzx/201910/t20191019_383680.shtml)
- 已核验入口：[行政许可结果](https://jxt.hubei.gov.cn/fbjd/xxgkml/xkfw/xzxkjg_jxt/)
- 已核验入口：[集中采购目录、标准、采购实施情况](https://jxt.hubei.gov.cn/fbjd/xxgkml/zfcg/jzcgml/)
- 已核验入口：[惠民政策](https://jxt.hubei.gov.cn/fbjd/xxgkml/gysyjs/hmhnhq/hmzc/)
- 已核验入口：[惠农政策](https://jxt.hubei.gov.cn/fbjd/xxgkml/gysyjs/hmhnhq/hnzc/)
- 已核验入口：[政策执行及落实情况](https://jxt.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/zczxjlsqk/)
- 已核验入口：[涉企行政检查公示专栏](https://jxt.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/sqxzjc/xzjczt/)
- 已核验入口：[行政检查标准](https://jxt.hubei.gov.cn/fbjd/xxgkml/qtzdgknr/sqxzjc/xzjcbz/)
- 已核验入口：[通知公告](http://jxt.hubei.gov.cn/fbjd/zc/qtzdgkwj/gwfb/)
- 已核验入口：[政策通知及解读](https://jxt.hubei.gov.cn/bmdt/ztzl/zjtx/zcwj/)
- 已核验入口：[无线电频率指配审批](https://jxt.hubei.gov.cn/bsfw/yjsfw/)
- 已核验入口：[政策通知](https://jxt.hubei.gov.cn/bmdt/ztzl/wqzt/wgchwtzxzz/zctz_zxzz/)
- 已核验入口：[相关文件](https://jxt.hubei.gov.cn/bmdt/ztzl/wqzt/sswgh/xgwj_sws/)
- 已核验入口：[政策及解读](https://jxt.hubei.gov.cn/bmdt/ztzl/xjzzyhd/zcjd/)
- 已核验入口：[政策及解读](https://jxt.hubei.gov.cn/bmdt/ztzl/cybzqxc/zcjjd/)
- 待复核：[页面](https://jxt.hubei.gov.cn/hdjl/tzxx/)；Page.goto: Timeout 12000ms exceeded. Call log:   - navigating to "https://jxt.hubei.gov.cn/hdjl/tzxx/", waiting until "domcontentloaded" 

### 24 黑龙江省工业和信息化厅

- 首页：https://gxt.hlj.gov.cn/
- 浏览器渲染/兜底页面：26。
- 已核验入口：[通知公告](https://gxt.hlj.gov.cn/gxt/c106958/list.shtml)
- 已核验入口：[政策解读](https://gxt.hlj.gov.cn/gxt/c106983/zfxxgk.shtml?tab=zcjd)
- 已核验入口：[政策](https://gxt.hlj.gov.cn/gxt/c106980/zfxxgk.shtml?tab=gkzc)
- 已核验入口：[结果公示](https://gxt.hlj.gov.cn/gxt/c107029/list.shtml)
- 已核验入口：[规范性文件](https://gxt.hlj.gov.cn/gxt/c106981/zfxxgk.shtml?tab=gfxwj)
- 已核验入口：[政策](https://gxt.hlj.gov.cn/gxt/c106979/zfxxgk.shtml?tab=gkzc)
- 已核验入口：[行政规章](https://gxt.hlj.gov.cn/common/search/24381ac95a7e40f2b2da8f8e8641f849?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[行政规范性文件](https://gxt.hlj.gov.cn/common/search/402de917ab914c70ae4ab82e8f6eacf2?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[其它文件](https://gxt.hlj.gov.cn/common/search/b9ba668b8ef94a49b08e91a64fb3c942?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[政策解读](https://gxt.hlj.gov.cn/common/search/18c00ce697ff4e14a2611a46f35f7cdf?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[行政许可](https://gxt.hlj.gov.cn/common/search/6bfd1ab01c854046b6128617e31f54db?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 25 南通市工业和信息化局

- 首页：https://gxj.nantong.gov.cn/
- 浏览器渲染/兜底页面：34。
- 已核验入口：[政策文件](https://gxj.nantong.gov.cn/ntsjxw/zcwj/zcwj.html)
- 已核验入口：[政策解读](https://gxj.nantong.gov.cn/ntsjxw/jdhy/jdhy.html)
- 已核验入口：[公示公告](https://gxj.nantong.gov.cn/ntsjxw/gggs/gggs.html)
- 已核验入口：[人事信息](https://gxj.nantong.gov.cn/ntsjxw/rsxx/rsxx.html)
- 已核验入口：[行政规范性文件](https://gxj.nantong.gov.cn/ntsjxw/gfxwj/gfxwj.html)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 26 中华人民共和国财政部

- 首页：https://www.mof.gov.cn/index.htm
- 浏览器渲染/兜底页面：12。
- 已核验入口：[政策发布](https://www.mof.gov.cn/zhengwuxinxi/zhengcefabu/)
- 已核验入口：[政策解读](https://www.mof.gov.cn/zhengwuxinxi/zhengcejiedu/)
- 已核验入口：[通知公告](https://www.mof.gov.cn/gkml/bulinggonggao/tongzhitonggao/)
- 已核验入口：[人事教育司](https://rjs.mof.gov.cn/)
- 已核验入口：[行政许可事项清单](https://tfs.mof.gov.cn/zt/fgfzl/xzspzdgg/spsxqd/)
- 已核验入口：[会计信息质量检查公告](https://jdjc.mof.gov.cn/jianchagonggao/)
- 已核验入口：[小微企业税费支持政策专栏](https://szs.mof.gov.cn/zt/sfzl/)
- 已核验入口：[财政部公告](https://www.mof.gov.cn/gkml/bulinggonggao/czbgg/)
- 已核验入口：[工作通知](https://kjs.mof.gov.cn/zt/kjfxcgc/gztz/)
- 已核验入口：[政策规定及解读](https://szs.mof.gov.cn/zt/mlqd_8464/zcgd/)
- 已核验入口：[残疾人事业发展补助资金](https://www.mof.gov.cn/zhuantihuigu/cczqzyzfglbf/zxzyzf_7788/cjrsyfzbzzj/)
- 已核验入口：[船舶报废拆解和船型标准化补贴](https://www.mof.gov.cn/zhuantihuigu/cczqzyzfglbf/zxzyzf_7788/cbbfcjhcxbzhbt/)
- 已核验入口：[政策规章](https://yss.mof.gov.cn/zhengceguizhang/)
- 已核验入口：[工作动态与通知](https://xzzf.mof.gov.cn/gzdtytz/)
- 已核验入口：[政策发布与解读](https://xzzf.mof.gov.cn/zcfbyjd/)
- 已核验入口：[政策法规](https://rjs.mof.gov.cn/zcfg/)
- 已核验入口：[--人事工作信息](https://rjs.mof.gov.cn/zt/kaoluzhuanti/)
- 已核验入口：[工作通知](https://kjs.mof.gov.cn/gongzuotongzhi/)
- 已核验入口：[政策发布](https://kjs.mof.gov.cn/zhengcefabu/)
- 已核验入口：[政策解读](https://kjs.mof.gov.cn/zhengcejiedu/)
- 已核验入口：[政策发布](https://gss.mof.gov.cn/gzdt/zhengcefabu/)
- 已核验入口：[政策发布](https://jkw.mof.gov.cn/zhengcefabu/)
- 已核验入口：[政策解读](https://jrs.mof.gov.cn/zhengcejiedu/)
- 已核验入口：[业务公告](https://zwgls.mof.gov.cn/ywgg/)
- 已核验入口：[政策法规](https://yss.mof.gov.cn/zhuantilanmu/dfzgl/zcfg/)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 27 江苏省财政厅

- 首页：https://czt.jiangsu.gov.cn/
- 浏览器渲染/兜底页面：0。
- 已核验入口：[政策发布更多](https://czt.jiangsu.gov.cn/col/col77309/index.html)
- 已核验入口：[政策解读更多](https://czt.jiangsu.gov.cn/col/col51149/index.html)
- 已核验入口：[公告公示更多](https://czt.jiangsu.gov.cn/col/col77314/index.html)
- 已核验入口：[惠企政策直达快享](https://czt.jiangsu.gov.cn/col/col90560/index.html)
- 已核验入口：[财政法规制度](https://czt.jiangsu.gov.cn/col/col77684/index.html)
- 已核验入口：[执法公示](https://czt.jiangsu.gov.cn/col/col92072/index.html)
- 已核验入口：[人事任免](https://czt.jiangsu.gov.cn/col/col51152/index.html)
- 已核验入口：[助企纾困财政政策](https://czt.jiangsu.gov.cn/col/col86456/index.html)
- 已核验入口：[政策原文](https://czt.jiangsu.gov.cn/col/col90561/index.html)
- 已核验入口：[政策解读](https://czt.jiangsu.gov.cn/col/col90562/index.html)
- 已核验入口：[政策宣传](https://czt.jiangsu.gov.cn/col/col90563/index.html)
- 已核验入口：[政策研究室](https://czt.jiangsu.gov.cn/col/col90915/index.html)
- 已核验入口：[政策法规处(行政审批处)](https://czt.jiangsu.gov.cn/col/col7808/index.html)
- 已核验入口：[人事教育处](https://czt.jiangsu.gov.cn/col/col7795/index.html)
- 已核验入口：[信用公示](https://czt.jiangsu.gov.cn/sgskjss/sgs/xzxkxx/list.do)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 28 湖北省财政厅

- 首页：https://czt.hubei.gov.cn/
- 浏览器渲染/兜底页面：13。
- 已核验入口：[涉企行政检查公示专栏](https://czt.hubei.gov.cn/bmdt/ztzl/sqxzjcgszl/)
- 已核验入口：[通知公告](https://czt.hubei.gov.cn/zfxxgk_GK2020/zc_GK2020/qtzdgkwj/)
- 已核验入口：[政策](https://czt.hubei.gov.cn/zfxxgk_GK2020/zc_GK2020/gfxwj_2020/)
- 已核验入口：[政策解读](https://czt.hubei.gov.cn/zfxxgk_GK2020/zc_GK2020/zcjd_GK2020/)
- 已核验入口：[政策问答平台](https://czt.hubei.gov.cn/bsfw/zcwd/)
- 已核验入口：[规范性文件库](https://czt.hubei.gov.cn/zfxxgk_GK2020/zc_GK2020/gfxwj_2020/gfxwjk/)
- 已核验入口：[行政许可结果](https://czt.hubei.gov.cn/zfxxgk_GK2020/fdzdgknr_GK2020/xkfw_GK2020/xzxkjg_GK2020/)
- 已核验入口：[惠民惠农政策和资金发放信息](https://czt.hubei.gov.cn/bmdt/ztzl/hmhnczbtzjykt/)
- 已核验入口：[资金文件](https://czt.hubei.gov.cn/zfxxgk_GK2020/fdzdgknr_GK2020/czzj_GK2020/zjwj/)
- 已核验入口：[惠企政策](https://czt.hubei.gov.cn/zfxxgk_GK2020/fdzdgknr_GK2020/hqzc/zcpghybf/)
- 已核验入口：[政策执行及落实情况](https://czt.hubei.gov.cn/zfxxgk_GK2020/fdzdgknr_GK2020/qtzdgknr_GK2020/zczxjlsqk/)
- 已核验入口：[市场监管规则和标准](https://czt.hubei.gov.cn/zfxxgk_GK2020/fdzdgknr_GK2020/qtzdgknr_GK2020/scjggzhbz/)
- 已核验入口：[来信公示](https://czt.hubei.gov.cn/hdjl/lxgs/)
- 已核验入口：[通知公告](https://czt.hubei.gov.cn/hbkjzc/tzgghbkjzc/)
- 已核验入口：[政策制度](https://czt.hubei.gov.cn/hbkjzc/zczj/)
- 已核验入口：[行政许可结果](https://czt.hubei.gov.cn/hbkjzc/xzxkjg/)
- 已核验入口：[政策解读](https://czt.hubei.gov.cn/hbkjzc/zczd/)
- 已核验入口：[重要政策](https://czt.hubei.gov.cn/bmdt/ztzl/hmhnczbtzjykt/zyzc/)
- 已核验入口：[政策解读](https://czt.hubei.gov.cn/bmdt/ztzl/hmhnczbtzjykt/zcjd/)
- 已核验入口：[【文字解读】关于《湖北省临时救助实施办法》政策解读](https://czt.hubei.gov.cn/bmdt/ztzl/hmhnczbtzjykt/zcjd/t_6007380.shtml)
- 已核验入口：[【文字解读】《湖北省到户产业奖补指引（试行）》政策解读](https://czt.hubei.gov.cn/bmdt/ztzl/hmhnczbtzjykt/zcjd/t_6007383.shtml)
- 已核验入口：[政策制度](https://czt.hubei.gov.cn/bmdt/ztzl/czfpzjzl/zczd/)
- 已核验入口：[公告公示](https://czt.hubei.gov.cn/bmdt/ztzl/czfpzjzl/gggs/)
- 已核验入口：[通知公告](https://czt.hubei.gov.cn/bmdt/ztzl/dfzfzqzl_6968/tzgg/)
- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。

### 29 黑龙江省财政厅

- 首页：https://czt.hlj.gov.cn/
- 浏览器渲染/兜底页面：26。
- 已核验入口：[通知公告](https://czt.hlj.gov.cn/czt/c110781/common_list.shtml)
- 已核验入口：[行政规范性文件](https://czt.hlj.gov.cn/czt/c110789/common_zfxxgk.shtml?tab=gfxwj)
- 已核验入口：[税收优惠政策](https://czt.hlj.gov.cn/czt/c110887/common_lists.shtml)
- 已核验入口：[涉企行政执法公示专栏](https://czt.hlj.gov.cn/czt/c116853/common_lists.shtml)
- 已核验入口：[政策解读](https://czt.hlj.gov.cn/czt/c110793/common_zfxxgk.shtml?tab=zcjd)
- 已核验入口：[部门文件](https://czt.hlj.gov.cn/czt/c110792/common_zfxxgk.shtml?tab=zcjd)
- 已核验入口：[政策](https://czt.hlj.gov.cn/czt/c110787/common_zfxxgk.shtml?tab=gkzc)
- 已核验入口：[行政规范性文件](https://czt.hlj.gov.cn/common/search/18c1620a2d524b47af1e9eb93edf0e96?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[其它文件](https://czt.hlj.gov.cn/common/search/c1c9de045c2147b59dc429737906970d?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[其它文件子栏目](https://czt.hlj.gov.cn/common/getChannelList?channelCode=c110790&websiteCodeName=czt)
- 已核验入口：[政策解读](https://czt.hlj.gov.cn/common/search/a6b8a91e4be54ebe9e2128707185aca4?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[政策解读子栏目](https://czt.hlj.gov.cn/common/getChannelList?channelCode=c110793&websiteCodeName=czt)
- 已核验入口：[涉企行政检查公示专栏](https://czt.hlj.gov.cn/czt/c110917/common_olists.shtml)
- 已核验入口：[政策文件链接](https://czt.hlj.gov.cn/czt/c116038/common_olist.shtml)
- 已核验入口：[涉企行政检查“六公示”](https://czt.hlj.gov.cn/czt/c116852/common_lists.shtml)
- 已核验入口：[政策制度](https://czt.hlj.gov.cn/common/search/b6f90d10dd5e403cbfaeb5ded92c419d?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 已核验入口：[部门文件](https://czt.hlj.gov.cn/common/search/c8e81f6e38444d0a9542c6f1a34ebb6a?_isAgg=true&_isJson=true&_pageSize=15&_template=index&page=1)
- 待复核：[页面](https://czt.hlj.gov.cn/czt/c110872/common_lists.shtml)；Page.goto: Timeout 15000ms exceeded. Call log:   - navigating to "https://czt.hlj.gov.cn/czt/c110872/common_lists.shtml", waiting until "domcontentloaded" 

### 30 南通市财政局

- 首页：https://czj.nantong.gov.cn/
- 浏览器渲染/兜底页面：71。
- 已核验入口：[政策文件](https://czj.nantong.gov.cn/ntsczj/zcwj/zcwj.html)
- 已核验入口：[政策解读](https://czj.nantong.gov.cn/ntsczj/zcjd/zcjd.html)
- 已核验入口：[公示公告](https://czj.nantong.gov.cn/ntsczj/gggs/gggs.html)
- 已核验入口：[人事信息](https://czj.nantong.gov.cn/ntsczj/rsrm/rsrm.html)
- 已核验入口：[规章及规范性文件](https://czj.nantong.gov.cn/ntsczj/gzjgfxwj/gzjgfxwj.html)
- 已核验入口：[涉企行政检查公示](https://czj.nantong.gov.cn/ntsczj/sqxzjcgs/sqxzjcgs.html)
- 已核验入口：[规章](https://czj.nantong.gov.cn/ntsczj/gz/gz.html)
- 已核验入口：[行政规范性文件](https://czj.nantong.gov.cn/ntsczj/gfxwj/gfxwj.html)
- 已核验入口：[检查标准](https://czj.nantong.gov.cn/ntsczj/jcbz/jcbz.html)
- 待复核：[页面](https://czj.nantong.gov.cn/truecms/staticJyh/\http:/nt.jszwfw.gov.cn/jszwfw/qlqd/deptlist.do?webId=6&type=&deptId=11320600014206763R)；Page.goto: Timeout 15000ms exceeded. Call log:   - navigating to "https://czj.nantong.gov.cn/truecms/staticJyh//http:/nt.jszwfw.gov.cn/jszwfw/qlqd/deptlist.do?webId=6&type=&deptId=11320600014206763R", waiting until "domcontentloaded" 
- 待复核：[页面](https://czj.nantong.gov.cn/ntsczj/xwfbh/content/\http:/nt.jszwfw.gov.cn/jszwfw/qlqd/deptlist.do?webId=6&type=&deptId=11320600014206763R)；浏览器访问返回 HTTP 404: https://czj.nantong.gov.cn/ntsczj/xwfbh/content//http:/nt.jszwfw.gov.cn/jszwfw/qlqd/deptlist.do?webId=6&type=&deptId=11320600014206763R
- 待复核：[页面](https://czj.nantong.gov.cn/jdhy/\http:/nt.jszwfw.gov.cn/jszwfw/qlqd/deptlist.do?webId=6&type=&deptId=11320600014206763R)；浏览器访问返回 HTTP 404: https://czj.nantong.gov.cn/jdhy//http:/nt.jszwfw.gov.cn/jszwfw/qlqd/deptlist.do?webId=6&type=&deptId=11320600014206763R

## 证据

原始逐页结果保存在本地 audit-results/ 下各轮检查目录的站点编号/audit.json，HTML 快照与其同目录。
完整控件记录见 audit-results/site-control-inventory.csv，包含站点、页面、控件类型、标签、请求入口、表单方法、下拉选项及公开控件参数。
栏目与导航链接见 audit-results/site-navigation-inventory.csv，按站点、目标 URL 和标签去重；未请求的外站入口不标记为通过。
