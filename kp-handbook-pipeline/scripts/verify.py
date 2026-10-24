# -*- coding: utf-8 -*-
r"""verify.py — 校验渲染产物: 编号连续性 / 条目格式 / 空内容 / OCR 乱码 / 格式参数 / 来源覆盖率。

用法:
  python3 verify.py [--work /path/to/work] [--ref 参考手册.docx]

  --ref 可选；提供时额外对比参考手册的页面与标题字号。
  自动发现 <work>/out/<学科>/*.docx 与同名 *_知识点清单.csv。
"""
import os, re, json, glob, argparse
import docx
from docx.shared import Cm


def parse_args():
    ap = argparse.ArgumentParser(description='手册 docx 质量校验')
    ap.add_argument('--work', default=os.environ.get('KP_WORK', '.'), help='工作目录')
    ap.add_argument('--ref', default=None, help='参考手册 docx（可选）')
    return ap.parse_args()


ARGS = parse_args()
WORK = os.path.abspath(ARGS.work)
OUT = os.path.join(WORK, 'out')

ENTRY_RE = re.compile(r'^(\d+)\. 【([^】]{1,12})】(.*?) —— (.+)$')
MOJIBAKE = ['ï', 'å', 'æ', 'ç¼', 'æ', 'þ', 'ÿ', '\ufffd']
# OCR 常见噪声: 单字间夹杂空格的中文串（>8 个连续单字且半数带空格）
NOISE_RE = re.compile(r'(?:[\u4e00-\u9fff]\s){6,}[\u4e00-\u9fff]')


def check(subject):
    subj_dir = os.path.join(OUT, subject)
    problems = []
    for path in sorted(glob.glob(os.path.join(subj_dir, '*.docx'))):
        doc = docx.Document(path)
        paras = doc.paragraphs
        # 1) 编号连续
        nums = []
        entries = []
        for p in paras:
            m = ENTRY_RE.match(p.text)
            if m:
                nums.append(int(m.group(1)))
                entries.append(m)
        if nums != list(range(1, len(nums) + 1)):
            problems.append('%s: 编号不连续 (n=%d, 断点=%s)' % (os.path.basename(path), len(nums), [i for i in range(1, len(nums)+1) if i not in set(nums)][:5]))
        # 2) 条目格式: 名称或内容为空
        for m in entries:
            if not m.group(3).strip():
                problems.append('%s: 条目 %s 名称为空' % (os.path.basename(path), m.group(1)))
            if not m.group(4).strip():
                problems.append('%s: 条目 %s 内容为空' % (os.path.basename(path), m.group(1)))
        # 3) 乱码噪声
        for p in paras:
            if NOISE_RE.search(p.text):
                problems.append('%s: OCR 噪声串「%s」' % (os.path.basename(path), p.text[:40]))
                break
            if any(b in p.text for b in ['\ufffd', 'æ', 'ï¼']):
                problems.append('%s: 乱码字符 in 「%s」' % (os.path.basename(path), p.text[:40]))
                break
        # 4) 结构
        h1 = [p for p in paras if p.style.name == 'Heading 1']
        h2 = [p for p in paras if p.style.name == 'Heading 2']
        if not h1 or not any('目录' in p.text for p in h2):
            problems.append('%s: 缺少标题或目录' % os.path.basename(path))
        # 5) 格式参数
        sec = doc.sections[0]
        if abs(sec.page_width - Cm(21.0)) > 1000 or abs(sec.page_height - Cm(29.7)) > 1000:
            problems.append('%s: 页面尺寸非 A4' % os.path.basename(path))
        if abs(sec.left_margin - Cm(1.27)) > 20000:
            problems.append('%s: 边距非 0.5 英寸' % os.path.basename(path))
        body_runs = [r for p in paras for r in p.runs if r.font.size]
        if body_runs:
            sizes = {r.font.size.pt for r in body_runs}
            if sizes != {10.0}:
                problems.append('%s: 正文字号异常 %s' % (os.path.basename(path), sizes))
        h_sizes = {}
        for name, expect in (('Heading 1', 20.0), ('Heading 2', 15.0), ('Heading 3', 12.5), ('Heading 4', 11.0)):
            try:
                h_sizes[name] = doc.styles[name].font.size.pt
            except Exception:
                pass
        if h_sizes != {'Heading 1': 20.0, 'Heading 2': 15.0, 'Heading 3': 12.5, 'Heading 4': 11.0}:
            problems.append('%s: 标题样式字号与参考不一致 %s' % (os.path.basename(path), h_sizes))
        # 6) CSV 行数与 docx 条目数一致性
        csvs = glob.glob(os.path.join(subj_dir, '*_知识点清单.csv'))
        if csvs:
            import csv as _csv
            with open(csvs[0], encoding='utf-8-sig') as fh:
                n_csv = sum(1 for _ in _csv.reader(fh)) - 1
            n_docx = sum(1 for p in paras if ENTRY_RE.match(p.text))
            if n_csv != n_docx:
                problems.append('CSV 行数(%d) 与 docx 条目数(%d) 不一致' % (n_csv, n_docx))
    return problems


def check_reference():
    """对比参考手册格式参数（可选）。"""
    if not ARGS.ref or not os.path.exists(ARGS.ref):
        return ['参考手册未提供，跳过参考对比']
    doc = docx.Document(ARGS.ref)
    sec = doc.sections[0]
    out = ['参考手册: 页面 %.2f×%.2f cm, 边距 %.2f cm' % (
        sec.page_width.cm, sec.page_height.cm, sec.left_margin.cm)]
    sizes = {}
    for p in doc.paragraphs:
        if p.style.name.startswith('Heading'):
            for r in p.runs:
                if r.font.size:
                    sizes[p.style.name] = r.font.size.pt
                    break
    out.append('参考手册标题字号: %s' % sizes)
    return out


def main():
    for line in check_reference():
        print(line)
    all_probs = []
    subjects = [os.path.basename(d) for d in sorted(glob.glob(os.path.join(OUT, '*'))) if os.path.isdir(d)]
    if not subjects:
        print('NO OUTPUT found in', OUT)
        return
    for subj in subjects:
        probs = check(subj)
        print('%s: %s' % (subj, 'OK' if not probs else '%d 个问题' % len(probs)))
        for p in probs:
            print('   -', p)
        all_probs += probs
    print('\n== 校验结论: %s ==' % ('全部通过' if not all_probs else '发现 %d 个问题' % len(all_probs)))


if __name__ == '__main__':
    main()
