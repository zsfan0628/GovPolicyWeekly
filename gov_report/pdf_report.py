"""Portable, embedded-font report layout shared by desktop and CLI exports."""

from __future__ import annotations

import io
import os
import re
import tempfile
import threading
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, HRFlowable, KeepTogether,
                               PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)
from .crawl_issues import report_issues


INK, MUTED, BLUE, GREEN = '#202C35', '#65737B', '#245D80', '#42766B'
WIDTH = A4[0] - 38 * mm
FONT_DIR = Path(__file__).resolve().parent.parent / 'assets' / 'fonts'
_FONT_LOCK = threading.Lock()


def register_fonts():
    with _FONT_LOCK:
        for weight in ('Regular', 'Medium', 'Bold'):
            name = 'GovSans' + weight
            if name not in pdfmetrics.getRegisteredFontNames():
                path = FONT_DIR / f'SourceHanSansCN-{weight}.ttf'
                if not path.is_file():
                    raise FileNotFoundError('报告字体缺失，请使用包含 assets/fonts 的完整软件包')
                pdfmetrics.registerFont(TTFont(name, str(path)))
        pdfmetrics.registerFontFamily('GovSansRegular', normal='GovSansRegular', bold='GovSansBold')


def safe_text(value):
    return escape(str(value or '')).replace('\n', '<br/>')


def source_link(label, url, color=BLUE):
    label = safe_text(label)
    try:
        parts = urlsplit(str(url or '').strip())
        valid = parts.scheme.lower() in {'http', 'https'} and parts.netloc and not parts.username and not parts.password
    except ValueError:
        valid = False
    if not valid:
        return label
    return f'<a href="{escape(str(url).strip(), quote=True)}" color="{color}">{label}</a>'


def clean_excerpt(value, title=''):
    """Only remove exact repetitions/title copies, never infer missing facts."""
    parts = re.split(r'[\n；]+', str(value or ''))
    result = []
    for part in parts:
        part = part.strip()
        if part and part != str(title).strip() and part not in result:
            result.append(part)
    return '\n'.join(result)


def grouped_records(records):
    policy, personnel = [], []
    for record in sorted(records, key=lambda r: str(r.get('publish_date', '')), reverse=True):
        (personnel if '人事任免' in str(record.get('category', '')) else policy).append(record)
    return [('A', '政策文件', policy), ('B', '人事任免', personnel)]


class Subheading(Flowable):
    def __init__(self, label, accent=BLUE):
        super().__init__()
        self.label, self.accent = label, accent
        self.height = 18
        self.keepWithNext = True

    def wrap(self, width, height):
        self.width = width
        return width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(colors.HexColor(self.accent))
        c.rect(12, 3, 2.5, 11, fill=1, stroke=0)
        c.setFont('GovSansBold', 9)
        c.drawString(21, 4, self.label)
        x = 31 + pdfmetrics.stringWidth(self.label, 'GovSansBold', 9)
        c.setStrokeColor(colors.HexColor('#D7E0E5'))
        c.setLineWidth(0.5)
        c.line(x, 8, self.width - 12, 8)


class ReportDocument(BaseDocTemplate):
    def __init__(self, target, period, total=0):
        super().__init__(target, pagesize=A4, leftMargin=19 * mm, rightMargin=19 * mm,
                         topMargin=63, bottomMargin=59,
                         title='政策与人事信息周报', author='GovPolicyWeekly')
        self.period, self.total = period, total
        self.addPageTemplates(PageTemplate('report', frames=[Frame(
            self.leftMargin, self.bottomMargin, self.width, self.height,
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=self.decorate))

    def decorate(self, canvas, doc):
        canvas.saveState()
        left, right = self.leftMargin, A4[0] - self.rightMargin
        canvas.setFillColor(colors.HexColor(BLUE))
        canvas.rect(left, A4[1] - 35, 20, 3, stroke=0, fill=1)
        canvas.setFont('GovSansRegular', 8)
        canvas.drawString(left + 29, A4[1] - 33, 'POLICY WEEKLY')
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawRightString(right, A4[1] - 33, self.period)
        canvas.drawString(left, 31, '政策与人事信息周报')
        canvas.drawRightString(right, 31, f'第 {doc.page} / {self.total or doc.page} 页')
        canvas.setStrokeColor(colors.HexColor('#D7E0E5'))
        canvas.setLineWidth(0.5)
        for y in (48, A4[1] - 48):
            canvas.line(left, y, right, y)
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if getattr(flowable, 'outline', None):
            title, key = flowable.outline
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, 0)


class Layout:
    def __init__(self, records, start, end, context):
        self.records, self.groups, self.context = records, grouped_records(records), context or {}
        self.issues = report_issues(self.context)
        self.period = f'{start:%Y-%m-%d} 至 {end:%Y-%m-%d}'
        self.styles = {
            'body': ParagraphStyle('body', fontName='GovSansRegular', fontSize=10, leading=15, wordWrap='CJK', spaceAfter=4, textColor=colors.HexColor(INK)),
            'stat': ParagraphStyle('stat', fontName='GovSansBold', fontSize=26, leading=33, textColor=colors.HexColor(BLUE)),
            'small': ParagraphStyle('small', fontName='GovSansRegular', fontSize=8.2, leading=12, textColor=colors.HexColor(MUTED), wordWrap='CJK'),
            'title': ParagraphStyle('title', fontName='GovSansBold', fontSize=23, leading=31, spaceAfter=10, wordWrap='CJK'),
            'heading': ParagraphStyle('heading', fontName='GovSansBold', fontSize=14, leading=21, spaceBefore=10, spaceAfter=9, keepWithNext=True, wordWrap='CJK'),
            'entry': ParagraphStyle('entry', fontName='GovSansMedium', fontSize=11.5, leading=17, wordWrap='CJK'),
            'cell': ParagraphStyle('cell', fontName='GovSansRegular', fontSize=8.7, leading=13, wordWrap='CJK'),
        }

    def p(self, value, style='body', raw=False):
        return Paragraph(value if raw else safe_text(value), self.styles[style])

    def heading(self, label, key=None):
        p = self.p(label, 'heading')
        if key:
            p.outline = (label, key)
        return p

    def box(self, content, background='#F4F5F6', accent=None):
        t = Table([[content]], colWidths=[WIDTH], splitInRow=1, hAlign='LEFT')
        commands = [('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(background)),
                    ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                    ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]
        if accent:
            commands.append(('LINEBEFORE', (0, 0), (0, -1), 3, colors.HexColor(accent)))
        t.setStyle(TableStyle(commands))
        return t

    def rows(self, data, widths):
        table = Table(data, colWidths=widths, repeatRows=1, splitInRow=1, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EDF3F6')),
            ('LINEBELOW', (0, 0), (-1, -1), 0.4, colors.HexColor('#D7E0E5')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        return table

    def coverage_notice(self):
        if self.context.get('coverage_note'):
            return str(self.context['coverage_note'])
        cov = self.context.get('coverage')
        if not cov:
            return '未提供逐站完成记录，不能据此确认全部站点采集完整。'
        counts = cov.get('counts', {})
        return (f"站点：{cov.get('complete', 0)} 完成 / {cov.get('partial', 0)} 部分失败 / "
                f"{cov.get('failed', 0)} 采集失败 / {cov.get('pending', 0)} 未完成。\n"
                f"待模型复判 {counts.get('llm_failed', 0)} 条；详情失败 {counts.get('detail_failed', 0)} 条。\n"
                f"非正文附件正常跳过 {counts.get('skipped_attachment', 0)} 个（不计为访问失败，未解析附件内容）。\n"
                '完成仅指配置范围内没有已知失败，不代表覆盖网站所有历史内容。')

    def story(self):
        story = [self.p('政策与人事信息周报', 'title'), self.p('农药化工企业信息参考 · ' + self.period, 'small'), Spacer(1, 14)]
        counts = [('收录总数', len(self.records)), ('政策文件', len(self.groups[0][2])), ('人事任免', len(self.groups[1][2]))]
        stats = [[self.p(n, 'stat') for label, n in counts], [self.p(label, 'small') for label, n in counts]]
        story += [Table(stats, colWidths=[WIDTH / 3] * 3), Spacer(1, 12),
                  self.p('人事优先归类，避免重复计数；日期按各分类倒序排列。', 'small'), Spacer(1, 10),
                  self.box(self.p(self.coverage_notice(), 'small'), '#FAF5EA')]
        if self.issues:
            story += [Spacer(1, 8), self.p(
                f'本次有 {len(self.issues)} 个页面访问异常或待核查，可能影响报告完整性。'
                f'<a href="#access-issues" color="{BLUE}"><b>查看文末明细</b></a>。', 'small', True)]
        story += [
                  self.heading('信息清单', 'list'), self.p('编号定位详情，标题打开原文。', 'small'), Spacer(1, 5)]
        for prefix, label, records in self.groups:
            if not records:
                continue
            group_heading = self.heading(label)
            group_heading.keepWithNext = False
            story.append(CondPageBreak(85))
            story.append(group_heading)
            rows = [[self.p(x, 'small') for x in ('编号', '日期', '发布单位', '标题')]]
            for i, r in enumerate(records, 1):
                key = f'{prefix}{i:02d}'
                rows.append([self.p(f'<a href="#{key}" color="{BLUE}">{key}</a>', 'cell', True),
                             self.p(r.get('publish_date', ''), 'cell'), self.p(r.get('source_name', ''), 'cell'),
                             self.p(source_link(r.get('title', ''), r.get('url', '')), 'cell', True)])
            story.append(self.rows(rows, [34, 64, 107, WIDTH - 205]))
        if not self.records:
            story += [self.p('本周期暂无收录条目。请同时核对采集覆盖和失败记录，不能将未完成采集视为没有相关信息。')]
        else:
            story.append(PageBreak())
            for prefix, label, records in self.groups:
                if not records:
                    continue
                story.append(self.heading(label + ' / 详细条目', 'details-' + prefix))
                for i, r in enumerate(records, 1):
                    story.append(KeepTogether(self.entry(f'{prefix}{i:02d}', r)))
        story += [PageBreak(), self.heading('附录 / 采集与判定记录', 'audit'),
                  self.box(self.p(self.coverage_notice(), 'small')), Spacer(1, 10)]
        stages = self.context.get('stages', {})
        if stages:
            descriptions = []
            for kind, label in [('list', '列表'), ('detail', '详情'), ('llm', '模型')]:
                data = stages.get(kind, {})
                descriptions.append(f"{label}阶段：{data.get('count', 0)} 次，错误 {data.get('errors', 0)} 次")
            story += [self.p('；'.join(descriptions) + '。次数不等于站点数。', 'small'), Spacer(1, 8)]
        for source in (self.context.get('coverage') or {}).get('sources', []):
            model_issues = [item for item in source.get('issues', []) if item.get('status') == 'llm_failed']
            if not model_issues:
                continue
            story.append(self.heading(source.get('name', '') + ' · ' + source.get('label', '待核查')))
            for item in model_issues:
                title = item.get('column') or item.get('title') or '待处理页面'
                story.append(self.p(source_link(title, item.get('url', '')), 'body', True))
                story.append(self.p(item.get('reason') or '未完成，需重试或核查。', 'small'))
        story.append(self.heading('条目判定依据'))
        for prefix, _, records in self.groups:
            for i, r in enumerate(records, 1):
                key = f'{prefix}{i:02d}'
                title = self.p(f'<a href="#{key}" color="{BLUE}">{key}</a> · '
                               + safe_text(r.get('title', '')), raw=True)
                method = r.get('decision_source') or '未记录'
                reason = r.get('llm_reason') or r.get('rule_reason') or '未记录具体判断理由。'
                story.append(KeepTogether([title, self.p('判定方式：' + str(method), 'small'),
                                           self.p(reason, 'small'), Spacer(1, 9)]))
        story += [self.heading('阅读说明'), self.p('摘要及变动提示来自采集结果，不等同于原文全文或人工核验。重复标题和完全重复片段仅在排版时去重，不补写缺失事实。模型是否参与以各条目的判定记录为准。', 'small')]
        if self.issues:
            story += [PageBreak(), self.heading('附录 / 访问异常与待核查页面', 'access-issues'),
                      self.p('以下为本次采集未完成的页面，不代表网站永久不可用。点击标题或地址可在浏览器手动访问；'
                             '未识别日期、正文或列表链接的页面属于提取待核查，不一定无法访问。非正文附件正常跳过另计，不混入本清单。', 'small'),
                      Spacer(1, 10)]
            for i, item in enumerate(self.issues, 1):
                label = item.get('title') or item.get('column') or item.get('url') or '未命名页面'
                url = item.get('url', '')
                stage = '列表 / 栏目' if item.get('kind') == 'list' else '详情'
                story += [KeepTogether([
                    self.box(self.p(f'<b>{i:02d}</b>　' + source_link(label, url), 'entry', True), '#EDF3F6', BLUE),
                    Spacer(1, 5), self.p(f"{item.get('source', '')} · {stage}", 'small'),
                    self.p(item.get('reason') or '未完成，需重试或人工核查。'),
                    self.p(source_link(url or '未记录地址', url), 'small', True),
                    Spacer(1, 10), HRFlowable(width='100%', thickness=0.4, color=colors.HexColor('#D7E0E5')),
                    Spacer(1, 12)])]
        return story

    def entry(self, key, r):
        accent = GREEN if key.startswith('B') else BLUE
        meta = ' · '.join(str(r.get(k) or '') for k in ('source_name', 'publish_date', 'related_directions') if r.get(k))
        title = f'<a name="{key}"/><b>{key}</b>　' + source_link(r.get('title', ''), r.get('url', ''), accent)
        header = self.box([self.p(title, 'entry', True), Spacer(1, 5), self.p(meta, 'small')],
                          '#EEF4F1' if key.startswith('B') else '#EDF3F6', accent)
        summary = clean_excerpt(r.get('summary'), r.get('title')) or '未提取到可独立阅读的摘要，请查看原文。'
        body = self.box(self.p('<b>内容摘要</b><br/>' + safe_text(summary), raw=True))
        parts = [header, Spacer(1, 8), body, Spacer(1, 7)]
        points = clean_excerpt(r.get('change_points'), r.get('title'))
        if points:
            parts += [Subheading('变动 / 调整提示（自动提取）', accent), self.p(points), Spacer(1, 5)]
        attachments = r.get('attachments') or []
        if attachments:
            parts.append(Subheading('附件', accent))
            for item in attachments:
                parts.append(self.p(source_link(item.get('name') or '附件', item.get('url', '')), 'small', True))
                parts.append(Spacer(1, 4))
        parts += [self.p(source_link('查看原文', r.get('url', '')), 'small', True), Spacer(1, 7),
                  HRFlowable(width='100%', thickness=0.8, color=colors.HexColor(accent)), Spacer(1, 14)]
        return parts


def export_report(records, path, start, end, context=None):
    register_fonts()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    layout = Layout(records, start, end, context)
    # A fresh second build keeps internal link destinations intact while adding total pages.
    probe = ReportDocument(io.BytesIO(), layout.period)
    probe.build(layout.story())
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.report-', suffix='.pdf', delete=False) as handle:
        temporary = Path(handle.name)
    try:
        document = ReportDocument(str(temporary), layout.period, probe.page)
        document.build(layout.story())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path
