# -*- coding: utf-8 -*-
r"""render.py — 把 plan/<学科>.json 渲染为仿《高中数学知识点背诵手册》格式的 docx 与 CSV。

plan JSON 结构:
  {"subject": "02_数学", "unit": "手册标题",
   "volumes": [{"name": "卷一...", "books": [{"name": "第1册...", "src": "来源",
                "chapters": [{"name": "章", "sections": [{"name": "节",
                    "entries": [{"t": "类型", "n": "名称", "c": "内容", "s": "来源"}]}]}]}]}]}

格式规格（实测自参考手册）:
  A4 纵向、四边距 0.5 英寸；正文 run 字体 ascii/hAnsi=<--font-latin>、eastAsia=<--font-ea>、10pt；
  Heading 1-4 加粗、颜色 #1F1F1F，字号 20/15/12.5/11pt；
  结构: H1 标题 → 斜体使用说明 → 统计行 → H2 目录 → H1 卷 / H2 册 / H3 章 / H4 节 / Normal 条目
  条目格式: N. 【类型】名称 —— 内容

用法:
  python3 render.py [--work /path/to/work] [--config config.json]
                   [--font-latin 'Maple Mono NF'] [--font-ea 'HYKaiTi S'] [学科 ...]

  --config  可选 JSON，提供每个学科的 unit/types/extra 说明；缺省用通用模板。
            自动发现 <work>/plan/*.json，文件名（去扩展名）即学科号。
"""
import os, re, json, csv, sys, glob, argparse
import docx
from docx.shared import Pt, Cm, RGBColor
from docx.oxml.ns import qn


def parse_args():
    ap = argparse.ArgumentParser(description='plan JSON → docx/CSV/md 渲染')
    ap.add_argument('--work', default=os.environ.get('KP_WORK', '.'), help='工作目录')
    ap.add_argument('--config', default=None, help='学科说明配置 JSON（可选）')
    ap.add_argument('--font-latin', default='Maple Mono NF', help='西文字体')
    ap.add_argument('--font-ea', default='HYKaiTi S', help='中文字体')
    ap.add_argument('subs', nargs='*', help='只渲染指定学科（缺省全部）')
    return ap.parse_args()


ARGS = parse_args()
WORK = os.path.abspath(ARGS.work)
PLAN_DIR = os.path.join(WORK, 'plan')

FONT_LATIN = ARGS.font_latin
FONT_EA = ARGS.font_ea

DEFAULT_META = {
    'types': '定义 / 定理性质 / 解法 / 易错 / 例题 / 附注',
    'extra': '6. 条目按学科实际结构归类；编纂时以教材与权威注本为准。',
}


def load_meta():
    """config 提供 per-subject 覆盖；其余用通用模板。"""
    cfg = {}
    if ARGS.config and os.path.exists(ARGS.config):
        cfg = json.load(open(ARGS.config, encoding='utf-8')).get('subjects', {})
    meta = {}
    for pf in sorted(glob.glob(os.path.join(PLAN_DIR, '*.json'))):
        subj = os.path.splitext(os.path.basename(pf))[0]
        if ARGS.subs and subj not in ARGS.subs:
            continue
        m = dict(DEFAULT_META)
        m.update(cfg.get(subj, {}))
        meta[subj] = m
    return meta


def style_doc(doc):
    st = doc.styles['Normal']
    st.font.name = FONT_LATIN
    st.font.size = Pt(10)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), FONT_EA)
    st.paragraph_format.line_spacing = 1.0
    for name, size in (('Heading 1', 20), ('Heading 2', 15), ('Heading 3', 12.5), ('Heading 4', 11)):
        try:
            stl = doc.styles[name]
        except KeyError:
            continue
        stl.font.name = FONT_LATIN
        stl.font.size = Pt(size)
        stl.font.bold = True
        stl.font.color.rgb = RGBColor(0x1F, 0x1F, 0x1F)
        stl.element.rPr.rFonts.set(qn('w:eastAsia'), FONT_EA)


def add_para(doc, text, style=None, size=None, bold=False, italic=False):
    p = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    r = p.add_run(text)
    r.font.name = FONT_LATIN
    r._element.rPr.rFonts.set(qn('w:eastAsia'), FONT_EA)
    if size:
        r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    return p


def render(subject, meta):
    plan = json.load(open(os.path.join(PLAN_DIR, subject + '.json'), encoding='utf-8'))
    unit = plan.get('unit') or meta.get('unit') or (subject + ' 知识点手册')
    out_dir = os.path.join(WORK, 'out', subject)
    os.makedirs(out_dir, exist_ok=True)

    # flatten
    vols = []
    for v in plan['volumes']:
        books = []
        for b in v['books']:
            chapters = []
            for ch in b['chapters']:
                secs = []
                for sec in ch['sections']:
                    secs.append((sec['name'], sec['entries']))
                chapters.append((ch['name'], secs))
            books.append((b['name'], chapters))
        vols.append((v['name'], books))

    n_entries = sum(len(es) for _, bs in vols for _, chs in bs for _, secs in chs for _, es in secs)
    n_books = sum(len(bs) for _, bs in vols)

    doc = docx.Document()
    style_doc(doc)
    for sec in doc.sections:
        sec.page_width = Cm(21.0)
        sec.page_height = Cm(29.7)
        sec.left_margin = Cm(1.27)
        sec.right_margin = Cm(1.27)
        sec.top_margin = Cm(1.27)
        sec.bottom_margin = Cm(1.27)

    # 标题
    add_para(doc, unit, style='Heading 1')
    # 使用说明
    add_para(doc, '使用说明', size=10, italic=True)
    notes = [
        '1. 本册按「卷—册—节」三级编排（册数与条目数见下方统计）。每条知识点独立成行、编号连续，可直接按编号自测。',
        '2. 条目格式：N. 【类型】名称 —— 内容。类型含：' + meta['types'] + '。',
        '3. 内容以本学期各科资料（复习资料·导学案教案·答案解析·教材课件·试卷精讲）为素材编纂，条目末尾的来源可在同目录 CSV 中按编号查询。',
        '4. 同一内容若来自多个来源（教材不同册、专题讲义、扫描版答案），分别成册收录，重复处可只背一册，以免丢失增量。',
        '5. 凡原资料/OCR 未能确证的信息已剔除或标注「（待核）」，背诵时以教材与权威注本为准。',
        meta['extra'],
    ]
    for t in notes:
        add_para(doc, t, size=10, italic=True)
    add_para(doc, '· 册数：%d ｜ 知识点条目：%d 条' % (n_books, n_entries), size=10)
    doc.paragraphs[-1].paragraph_format.left_indent = Cm(0.6)
    add_para(doc, '')
    # 目录
    add_para(doc, '目录', style='Heading 2')
    for vname, books in vols:
        add_para(doc, vname, size=10)
        for bname, chapters in books:
            cnt = sum(len(es) for _, es in chapters)
            add_para(doc, '　%s（%d 条）' % (bname, cnt), size=10)
    add_para(doc, '')

    # 正文
    n = 0
    rows = []
    for vname, books in vols:
        add_para(doc, vname, style='Heading 1')
        for bname, chapters in books:
            add_para(doc, bname, style='Heading 2')
            for chname, secs in chapters:
                add_para(doc, chname, style='Heading 3')
                for secname, entries in secs:
                    add_para(doc, secname, style='Heading 4')
                    for e in entries:
                        n += 1
                        content = e['c'].strip()
                        if content and not content.endswith(('。', '；', '！', '？', '：', '.', '»')):
                            content += '。'
                        line = '%d. 【%s】%s —— %s' % (n, e['t'], e['n'], content)
                        add_para(doc, line, size=10)
                        rows.append([n, vname, bname, chname, secname, e['t'], e['n'], content, e.get('s', '')])
            add_para(doc, '')

    docx_path = os.path.join(out_dir, unit + '.docx')
    doc.save(docx_path)

    # CSV
    csv_path = os.path.join(out_dir, unit + '_知识点清单.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['编号', '卷', '册', '章', '节', '类型', '名称', '内容', '来源'])
        w.writerows(rows)

    # Markdown 存档
    md = ['# ' + unit, '', '> 依据各科资料编纂；格式仿《高中数学知识点背诵手册》。', '']
    md.append('· 册数：%d ｜ 知识点条目：%d 条' % (n_books, n_entries))
    md.append('')
    for r in rows:
        md.append('## %s / %s' % (r[1], r[2]))
        md.append('### %s / %s' % (r[3], r[4]))
        md.append('%d. 【%s】%s —— %s' % (r[0], r[5], r[6], r[7]))
        md.append('')
    open(os.path.join(out_dir, unit + '.md'), 'w', encoding='utf-8').write('\n'.join(md))

    print('%s: 册数=%d, 条目=%d -> %s' % (subject, n_books, n_entries, docx_path))
    return {'subject': subject, 'books': n_books, 'entries': n_entries}


def main():
    meta = load_meta()
    if not meta:
        print('NO PLAN found in', PLAN_DIR)
        return
    total = 0
    for s in meta:
        total += render(s, meta[s])['entries']
    print('TOTAL entries:', total)


if __name__ == '__main__':
    main()
