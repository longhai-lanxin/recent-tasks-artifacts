# -*- coding: utf-8 -*-
r"""dedupe.py — 按规范化文本 SHA1 折叠重复副本，生成去重语料。

输入: <work>/extracted/<学科>/*.txt + <work>/extracted/manifest.json
输出: <work>/clean/<学科>/<NNN>__<名>.txt   （去重后的唯一文本）
      <work>/clean/index.json               （唯一文件索引 + 重复组）

用法: python3 dedupe.py [--work /path/to/work]
"""
import os, re, json, hashlib, glob, shutil, argparse


def parse_args():
    ap = argparse.ArgumentParser(description='规范化 SHA1 去重')
    ap.add_argument('--work', default=os.environ.get('KP_WORK', '.'), help='工作目录')
    return ap.parse_args()


ARGS = parse_args()
WORK = os.path.abspath(ARGS.work)
EXTRACTED = os.path.join(WORK, 'extracted')
CLEAN = os.path.join(WORK, 'clean')


def norm_for_hash(t):
    t = re.sub(r'<!--.*?-->', '', t, flags=re.S)
    t = re.sub(r'===\s*第?\d+页\s*===', '', t)
    t = re.sub(r'\s+', '', t)
    return t


def main():
    shutil.rmtree(CLEAN, ignore_errors=True)
    manifest = {m['file']: m for m in json.load(open(os.path.join(EXTRACTED, 'manifest.json'), encoding='utf-8'))}
    index = []
    for subj in sorted(os.listdir(EXTRACTED)):
        subj_dir = os.path.join(EXTRACTED, subj)
        if not os.path.isdir(subj_dir):
            continue
        groups = {}
        for fp in sorted(glob.glob(os.path.join(subj_dir, '*.txt'))):
            fn = os.path.basename(fp)
            text = open(fp, encoding='utf-8').read()
            h = hashlib.sha1(norm_for_hash(text).encode('utf-8')).hexdigest()
            groups.setdefault(h, []).append((fn, text))
        out_dir = os.path.join(CLEAN, subj)
        os.makedirs(out_dir, exist_ok=True)
        n = 0
        for h, items in sorted(groups.items(), key=lambda kv: kv[1][0][0]):
            n += 1
            fn0, text = items[0]
            m = manifest.get(fn0, {})
            out_fn = '%03d__%s.txt' % (n, re.sub(r'^\d+__', '', os.path.splitext(fn0)[0]))
            with open(os.path.join(out_dir, out_fn), 'w', encoding='utf-8') as fh:
                fh.write(text)
            index.append({'subject': subj, 'file': out_fn, 'source': m.get('path', fn0),
                          'chars': len(re.sub(r'\s+', '', text)), 'dupes': [manifest.get(f, {}).get('path', f) for f, _ in items[1:]]})
        print('%-8s 唯一文件 %3d / 原始 %3d' % (subj, len(groups), len(glob.glob(os.path.join(subj_dir, '*.txt')))))
    json.dump(index, open(os.path.join(CLEAN, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    total_u = len(index)
    total_d = sum(len(x['dupes']) for x in index)
    print('\n== 唯一文件 %d 个，折叠重复副本 %d 个 ==' % (total_u, total_d))


if __name__ == '__main__':
    main()
