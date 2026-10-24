# -*- coding: utf-8 -*-
r"""mkbatch.py — 把 clean/ 下选中的文件合并为一个带文件头的批次文本，供通读。

用法: python3 mkbatch.py --work /path/to/work <学科号> <输出文件> <源路径子串1> [子串2 ...]
  子串对 clean/index.json 的 source 做匹配（任一子串命中即可）。
"""
import os, re, json, sys, argparse


def parse_args():
    ap = argparse.ArgumentParser(description='合并批次文本')
    ap.add_argument('--work', default=os.environ.get('KP_WORK', '.'), help='工作目录')
    ap.add_argument('subj', help='学科号（clean/ 下的目录名）')
    ap.add_argument('out', help='输出文件路径')
    ap.add_argument('pats', nargs='+', help='源路径子串，任一命中即选中')
    return ap.parse_args()


ARGS = parse_args()
WORK = os.path.abspath(ARGS.work)


def main():
    subj, out, pats = ARGS.subj, ARGS.out, ARGS.pats
    idx = json.load(open(os.path.join(WORK, 'clean/index.json'), encoding='utf-8'))
    picked = [x for x in idx if x['subject'] == subj and any(p in x['source'] for p in pats)]
    if not picked:
        print('NO MATCH for', pats)
        return
    parts = []
    total = 0
    for x in picked:
        text = open(os.path.join(WORK, 'clean', subj, x['file']), encoding='utf-8').read()
        text = re.sub(r'<!--.*?-->\n?', '', text, count=1)
        parts.append('\n===== FILE: %s (%d字) =====\n%s' % (x['source'], len(text), text))
        total += len(text)
    open(out, 'w', encoding='utf-8').write('\n'.join(parts))
    print('picked %d files, %d chars -> %s' % (len(picked), total, out))


if __name__ == '__main__':
    main()
