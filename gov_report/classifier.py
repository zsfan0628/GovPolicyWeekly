from __future__ import annotations

import re
from urllib.parse import urlparse

from .parser import split_sentences, clean_text


# 严格模式的思路：
# 1. “人事任免”必须是任免/任前公示/人选公示等正式信息，不能因为正文里出现“领导干部”就算。
# 2. “政策文件”必须有正式文件/公示/公告/通知/批复/解读/行政许可等形态。
# 3. 只是在新闻正文中引用/提到某个政策文件，不等于该网页是在发布政策文件。

GENERIC_TITLES = {
    "首页",
    "网站首页",
    "通知公告",
    "政策文件",
    "工作动态",
    "新闻动态",
    "视频",
    "更多",
    "查看更多",
    "中华人民共和国生态环境部",
    "中华人民共和国农业农村部",
    "中华人民共和国应急管理部",
    "中华人民共和国工业和信息化部",
    "国家发展和改革委员会",
    "湖北省经济和信息化厅",
    "湖北省农业农村厅",
    "江苏省农业农村厅",
    "江苏省生态环境厅",
    "江苏省应急管理厅",
}

BAD_TITLE_SNIPPETS = [
    "您访问的链接即将离开",
    "网站技术支持电话",
    "您的浏览器不支持 video",
]

NEWS_EXCLUDE_TERMS = [
    "召开会议",
    "召开常务会议",
    "专题会议",
    "视频会议",
    "会议召开",
    "召开党委",
    "召开党组",
    "举行",
    "举办",
    "启动仪式",
    "调研",
    "会见",
    "出席",
    "致辞",
    "座谈会",
    "推进会",
    "专题培训班",
    "理论学习",
    "支委扩大会议",
    "党支部",
    "开展专题活动",
    "新闻联播",
    "媒体报道",
    "湖北日报报道",
    "央视",
    "视频",
    "短视频",
    "警示片",
    "主题海报",
    "喜报",
]

# 标题里出现这些，通常是“网页本身在发布/公示/解读/征求/审批某个事项”的强信号。
# 注意：不要把“高标准完成升级”里的“标准”、新闻里提到“报告”这类弱词直接当成政策文件。
POLICY_FORMAL_TITLE_TERMS = [
    "通知",
    "函",
    "意见",
    "公告",
    "公示",
    "通报",
    "批复",
    "决定",
    "办法",
    "规定",
    "规程",
    "细则",
    "方案",
    "指南",
    "目录",
    "清单",
    "名单",
    "申报",
    "征集",
    "公开征求",
    "政策解读",
    "解读",
    "行政许可",
    "审批决定",
    "受理情况",
    "许可",
    "延续",
    "注册",
    "备案",
    "令",
]

POLICY_STANDARD_TITLE_PATTERNS = [
    "强制性国家标准",
    "国家标准",
    "行业标准",
    "地方标准",
    "标准制修订",
    "标准制定",
    "标准修订",
    "标准化工作要点",
    "标准体系",
    "征求意见稿",
]

# 标题虽然有政策词，但常见于新闻/活动稿，必须交给 LLM 或谨慎处理，不能规则直收。
POLICY_MENTION_ONLY_HINTS = [
    "锚定",
    "依据",
    "根据",
    "按照",
    "学习",
    "贯彻",
    "落实",
    "围绕",
    "解读会",
    "培训",
    "宣贯",
    "活动",
    "完成升级",
    "赋能",
]

# 即使标题里没有“关于”，这些栏目/URL也往往是正式文件栏目。
POLICY_URL_HINTS = [
    "xxgk",
    "govpublic",
    "zfxxgk",
    "zcwj",
    "zc_GK",
    "zcjd",
    "fdzdgknr",
    "wjgs",
    "gongshi",
    "gggs",
    "nscxmgs",
    "jsxmgs",
    "xzxk",
    "tzgg",
    "tz/",
    "gk/",
]

# v5.2：政策栏目判断。只要属于政策/政府信息公开/通知公告等栏目，且标题是正式文种，
# 就属于“脚本确定可以直接通过”的政策文件候选，不再强制要求农药化工关键词。
POLICY_COLUMN_TEXT_HINTS = [
    "当前位置", "政府信息公开", "政务公开", "法定主动公开内容", "政策", "政策文件",
    "其他主动公开文件", "规范性文件", "部门文件", "通知公告", "公告公示",
    "政策解读", "法规文件", "行政许可", "文件公开", "公开目录",
]

POLICY_COLUMN_URL_HINTS = [
    "/fbjd/zc/", "/zfxxgk/", "/xxgk/", "/govpublic/", "/gk/", "/zcwj/",
    "/gfwj/", "/fdzdgknr/", "/qtzdgkwj", "/zcjd/", "/wjgs/",
    "/tzgg/", "/gggs/", "/xzxk/", "/zc_gk", "/c115425/",
]

OFFICIAL_DOCUMENT_TYPES = [
    "通知", "函", "复函", "决定", "公告", "公示", "通报", "批复", "意见",
    "方案", "办法", "规定", "细则", "规程", "指南", "目录", "清单", "令",
    "解读", "申报", "征集", "印发", "转发", "公布", "发布",
]

PERSONNEL_TITLE_TERMS = [
    "人事任免",
    "干部任免",
    "任免通知",
    "任职通知",
    "免职通知",
    "职务任免",
    "任前公示",
    "干部公示",
    "人选公示",
    "任职前公示",
    "拟任",
    "拟提拔",
]

PERSONNEL_TEXT_PATTERNS = [
    re.compile(r"(任命|决定任命|聘任|拟任|免去|不再担任).{0,50}(同志|职务|主任|副主任|厅长|副厅长|局长|副局长|处长|副处长|秘书长)"),
    re.compile(r"现对.{0,50}(拟担任|拟任|任职).{0,50}(予以|进行).{0,20}公示"),
]

PERSONNEL_FALSE_POSITIVE_TERMS = [
    "领导干部专题培训",
    "领导干部警示教育",
    "新任县乡党政领导干部专题培训",
    "干部教育培训",
    "理论学习中心组",
    "支委扩大会议",
    "党组织开展",
]

BUSINESS_RELEVANCE_TERMS = [
    # 农药/农资
    "农药",
    "农药登记",
    "农药生产",
    "农药经营",
    "禁限用农药",
    "农资",
    "植保",
    # 化工/危化品
    "化工",
    "石油化工",
    "精细化工",
    "危险化学品",
    "危化品",
    "重大危险源",
    "油气储存",
    "涉氨制冷",
    "有限空间",
    # 企业安全/环保/排污
    "企业安全生产",
    "生产经营单位",
    "安全生产标准化企业",
    "危险废物",
    "危废",
    "固废",
    "挥发性有机物",
    "VOCs",
    "排污许可",
    "排污登记",
    "污染防治",
    "环境影响评价",
    "环评",
    "生态工业园区",
    # 工信/产业扶持
    "工业企业",
    "技术改造",
    "智能制造",
    "绿色工厂",
    "专精特新",
    "中小企业",
    "专项资金",
    "财政补贴",
    "产业扶持",
    "项目申报",
]

TOO_BROAD_POLICY_TERMS = {
    "安全生产",
    "生态环境",
    "支持",
    "补贴",
    "奖励",
    "智能制造",
    "标准化",
}


PROJECT_EIA_EXCLUDE_TERMS = [
    "建设项目环境影响评价文件受理情况",
    "环境影响评价文件受理情况",
    "建设项目环境影响评价文件拟进行审查",
    "环境影响评价文件拟进行审查",
    "环境影响报告书审批决定",
    "环境影响报告表审批决定",
    "环境影响报告书》审批决定",
    "环境影响报告表》审批决定",
    "环评审批决定公告",
    "环评文件受理公示",
    "环评文件拟审查公示",
    "项目环境影响报告书",
    "项目环境影响报告表",
    "建设项目环境影响报告书",
    "建设项目环境影响报告表",
]

PROJECT_EIA_URL_HINTS = [
    "jsxm",
    "nscxmgs",
    "jsxmgs",
    "gongshi/gsq",
    "hjyxpj",
]


def contains_any(text: str, keywords: list[str]) -> bool:
    text = text or ""
    return any(k and k in text for k in keywords)


def matched_keywords(text: str, keywords: list[str]) -> list[str]:
    text = text or ""
    return [k for k in keywords if k and k in text]


def is_bad_or_generic_title(title: str, source_name: str = "") -> bool:
    t = clean_text(title or "")
    if not t:
        return True
    if t in GENERIC_TITLES:
        return True
    if source_name and t == source_name:
        return True
    if any(x in t for x in BAD_TITLE_SNIPPETS):
        return True
    if len(t) <= 2:
        return True
    return False


def looks_like_news_or_meeting(title: str) -> bool:
    t = title or ""
    return any(k in t for k in NEWS_EXCLUDE_TERMS)


def looks_like_project_eia_publicity(title: str, text: str, url: str = "") -> bool:
    """单个建设项目环评受理/拟审查/审批公告，不按政策文件收录。

    这类页面是政府网站公示，但本质是具体项目材料或审批流程信息，
    不是面向农药化工企业发展的政策文件。
    """
    combined = clean_text(f"{title}\n{text[:1500]}")
    path = urlparse(url or "").path.lower()
    if any(k in combined for k in PROJECT_EIA_EXCLUDE_TERMS):
        return True
    if any(h in path for h in PROJECT_EIA_URL_HINTS) and any(k in combined for k in ["项目名称", "建设单位", "环境影响评价机构", "受理日期", "公示期"]):
        return True
    return False


def looks_like_personnel(title: str, text: str) -> bool:
    combined = f"{title}\n{text[:1200]}"
    if any(k in combined for k in PERSONNEL_FALSE_POSITIVE_TERMS):
        # 标题本身是正式任免/公示时仍允许。
        if not any(k in title for k in PERSONNEL_TITLE_TERMS):
            return False
    if any(k in title for k in PERSONNEL_TITLE_TERMS):
        return True
    if "人事" in title and ("任免" in combined or "公示" in combined):
        return True
    return any(p.search(combined) for p in PERSONNEL_TEXT_PATTERNS)


def detect_official_document_type(title: str, text: str = "") -> str:
    """识别正式文种。注意“函”是单字，必须在标题中以“关于...函/复函”形式出现。"""
    t = clean_text(title or "")
    head = clean_text(text[:500] or "")
    combined = f"{t}\n{head}"
    if "政策解读" in t or t.startswith(("文字解读", "图文解读", "一图读懂")):
        return "解读"
    if re.search(r"^.+令（?第?[0-9一二三四五六七八九十百]+号", t):
        return "令"
    if "复函" in t:
        return "复函"
    if re.search(r"关于.{2,80}函$", t) or re.search(r"关于.{2,80}的函", t):
        return "函"
    for term in OFFICIAL_DOCUMENT_TYPES:
        if term == "函":
            continue
        if term in t:
            return term
    # 标题不明显时，正文开头有“现印发/现发布/现公告”等，也算正式文种。
    for term in ["通知", "公告", "公示", "决定", "批复", "意见", "方案", "办法", "规定", "指南", "目录", "清单"]:
        if term in combined[:700] and any(x in combined[:700] for x in ["现印发", "现发布", "现公布", "现予以", "请遵照", "请认真贯彻", "公开征求"]):
            return term
    return ""


def looks_in_policy_column(title: str, text: str, url: str = "", context: str = "") -> bool:
    combined = clean_text(f"{title}\n{context}\n{text[:1200]}")
    path = urlparse(url or "").path.lower()
    if any(h.lower() in path for h in POLICY_COLUMN_URL_HINTS):
        return True
    return any(k in combined for k in POLICY_COLUMN_TEXT_HINTS)


def looks_like_formal_policy_doc(title: str, text: str, url: str = "", context: str = "") -> bool:
    """判断网页是否“形态上像正式政策/公示/审批/解读页面”。

    这里故意保守：
    - 标题里的“高标准”“报告”“工作动态”不能直接算政策文件；
    - 正文中只是引用“根据某文件”也不能算，需要标题或栏目本身有正式发布动作。
    真正拿不准的候选会交给 GPT 复判。
    """
    t = clean_text(title or "")
    path = urlparse(url or "").path.lower()
    head = clean_text(text[:1800])
    official_type = detect_official_document_type(t, text)
    in_policy_column = looks_in_policy_column(t, text, url=url, context=context)

    # v5.2：政策栏目 + 正式文种，直接认为形态上是政策文件。
    # 例如：通知、函、决定、公告、公示、批复、意见、方案、办法、解读等。
    if in_policy_column and official_type:
        return True

    # 标题中有“关于……通知/公告/公示/批复/方案/指南”等结构，通常是正式文件。
    if t.startswith("关于") and (official_type or any(k in t for k in POLICY_FORMAL_TITLE_TERMS)):
        return True

    # 明确的行政许可、审批、公示、征求意见、政策解读、名单公示等。
    strong_title_terms = [
        "行政许可", "公开征求", "征求意见",
        "政策解读", "一图读懂", "申报指南", "项目申报", "专项资金", "名单公示",
        "人选公示", "任前公示", "拟推荐", "许可延续",
    ]
    if any(k in t for k in strong_title_terms):
        return True

    # 标准类必须有“国家标准/行业标准/标准制修订/征求意见稿”等完整表达，避免误收“高标准”。
    if any(k in t for k in POLICY_STANDARD_TITLE_PATTERNS):
        return True

    # URL 在政府信息公开/政策栏目时，正文前部也必须出现正式文件发布动作。
    if any(h.lower() in path for h in POLICY_URL_HINTS):
        formal_head_patterns = [
            "现予以公布", "现予以公告", "现予以公示", "现公开征求", "现将", "予以发布",
            "印发", "发布", "修订", "废止", "施行", "申报", "受理", "审批", "批复", "许可",
        ]
        return any(k in f"{t}\n{head}" for k in POLICY_FORMAL_TITLE_TERMS) and any(p in head for p in formal_head_patterns)

    return False


def is_business_related(title: str, text: str, keywords: dict[str, list[str]]) -> tuple[bool, list[str]]:
    combined = f"{title}\n{text}"
    raw_hits = matched_keywords(combined, keywords.get("policy", []))
    strong_hits = [k for k in matched_keywords(combined, BUSINESS_RELEVANCE_TERMS) if k not in TOO_BROAD_POLICY_TERMS]
    # 只有“安全生产/生态环境/支持”等宽泛词时，不足以说明和农药化工企业发展相关。
    if strong_hits:
        return True, unique_keep_order(raw_hits + strong_hits)
    return False, raw_hits


def classify(title: str, text: str, keywords: dict[str, list[str]], url: str = "", source_name: str = "", strict: bool = True, context: str = "") -> dict[str, object]:
    title = clean_text(title or "")
    text = clean_text(text or "")
    combined = f"{title}\n{text}"

    reject_reasons: list[str] = []
    if is_bad_or_generic_title(title, source_name=source_name):
        reject_reasons.append("标题为网站名/栏目名/跳转提示，疑似非详情页")

    personnel = looks_like_personnel(title, text)
    business_related, policy_hits = is_business_related(title, text, keywords)
    project_eia_like = looks_like_project_eia_publicity(title, text, url=url)
    in_policy_column = looks_in_policy_column(title, text, url=url, context=context)
    official_document_type = detect_official_document_type(title, text)
    formal_policy = looks_like_formal_policy_doc(title, text, url=url, context=context) and not project_eia_like
    news_like = looks_like_news_or_meeting(title)

    if project_eia_like:
        reject_reasons.append("单个建设项目环评受理/拟审查/审批决定类公示，属于项目文件，不按政策文件收录")

    categories: list[str] = []

    if personnel and not is_bad_or_generic_title(title, source_name=source_name):
        categories.append("人事任免")

    if strict:
        # 严格模式：
        # - 政策栏目 + 正式文种，按用户口径直接算政策文件；
        # - 否则仍要求“正式文件形态 + 企业相关”。普通会议/调研/报道不收。
        if formal_policy and not is_bad_or_generic_title(title, source_name=source_name):
            if in_policy_column and official_document_type:
                categories.append("政策文件")
            elif business_related:
                if news_like and not any(k in title for k in ["通知", "函", "公告", "公示", "通报", "批复", "决定", "办法", "规定", "方案", "指南", "标准", "目录", "令"]):
                    reject_reasons.append("标题像会议/活动/报道，不按政策文件收录")
                else:
                    categories.append("政策文件")
            elif not personnel:
                reject_reasons.append("像正式文件，但与农药化工企业发展相关性不足；若属于政策栏目正式文种则应直接通过")
        else:
            if not formal_policy and business_related:
                reject_reasons.append("仅命中行业词，但不像正式政策/公示/通知")
            if formal_policy and not business_related and not personnel:
                reject_reasons.append("像正式文件，但与农药化工企业发展相关性不足")
    else:
        # 宽松模式：保留旧版逻辑，但仍排除明显错误标题。
        if business_related and not is_bad_or_generic_title(title, source_name=source_name):
            categories.append("政策文件")

    categories = unique_keep_order(categories)
    change_hits = matched_keywords(combined, keywords.get("change", []))

    return {
        "is_relevant": bool(categories),
        "categories": categories,
        "personnel_hits": matched_keywords(combined, keywords.get("personnel", [])),
        "policy_hits": policy_hits,
        "change_hits": change_hits,
        "related_directions": infer_related_directions(combined),
        "reject_reasons": reject_reasons,
        "formal_policy": formal_policy,
        "business_related": business_related,
        "news_like": news_like,
        "project_eia_like": project_eia_like,
        "in_policy_column": in_policy_column,
        "official_document_type": official_document_type,
    }


def infer_related_directions(text: str) -> list[str]:
    mapping = {
        "农药/农资": ["农药", "农资", "植保", "禁限用农药", "农药经营", "农药登记"],
        "化工/危化品": ["化工", "危险化学品", "危化品", "重大危险源", "油气储存", "涉氨制冷", "有限空间"],
        "生态环境/排污": ["环境影响评价", "环评", "排污许可", "排污登记", "污染防治", "VOCs", "挥发性有机物", "危险废物", "危废", "固废", "生态工业园区"],
        "安全生产": ["企业安全生产", "生产经营单位", "安全生产标准化企业", "重大事故隐患", "危险化学品安全"],
        "产业扶持/项目申报": ["产业扶持", "项目申报", "专项资金", "财政补贴", "奖励", "申报指南", "中小企业", "专精特新"],
        "工信/技改": ["工业企业", "技术改造", "智能制造", "绿色工厂", "标准化", "工业母机"],
    }
    directions = []
    for name, kws in mapping.items():
        if contains_any(text, kws):
            directions.append(name)
    return directions


def make_summary(title: str, text: str, keywords: dict[str, list[str]], max_chars: int = 320) -> str:
    """规则版精简摘要：优先选包含正式文件/企业相关/变动关键词的句子。"""
    text = clean_text(text)
    if not text:
        return ""
    key_pool = (
        POLICY_FORMAL_TITLE_TERMS
        + BUSINESS_RELEVANCE_TERMS
        + keywords.get("change", [])
        + keywords.get("personnel", [])
    )
    sents = split_sentences(text)
    scored = []
    bad_fragments = ["来源", "打印", "关闭", "分享", "扫一扫", "网站技术支持电话", "您的浏览器不支持 video", "长江流域生态环境监督管理局"]
    for idx, sent in enumerate(sents):
        if len(sent) < 10:
            continue
        score = sum(2 for k in key_pool if k in sent)
        if "关于" in sent[:8] or "现将" in sent[:8]:
            score += 2
        if any(k in sent for k in bad_fragments):
            score -= 6
        if score > 0:
            scored.append((score, -idx, sent))
    if scored:
        picked = [s for _, _, s in sorted(scored, reverse=True)[:3]]
    else:
        picked = [s for s in sents if not any(k in s for k in bad_fragments)][:2]
    summary = "；".join(picked)
    return trim(summary, max_chars)


def extract_change_points(text: str, keywords: dict[str, list[str]], max_points: int = 5, max_chars_each: int = 180) -> list[str]:
    change_keywords = keywords.get("change", [])
    points = []
    for sent in split_sentences(text):
        if len(sent) < 8:
            continue
        if any(k in sent for k in ["网站技术支持电话", "您的浏览器不支持 video", "长江流域生态环境监督管理局"]):
            continue
        if contains_any(sent, change_keywords):
            points.append(trim(sent, max_chars_each))
        if len(points) >= max_points:
            break
    return points


def trim(text: str, max_chars: int) -> str:
    text = clean_text(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def unique_keep_order(items):
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            out.append(item)
            seen.add(item)
    return out
