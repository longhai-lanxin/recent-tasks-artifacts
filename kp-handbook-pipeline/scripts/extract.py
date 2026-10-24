# -*- coding: utf-8 -*-
r"""extract.py — 从素材目录提取纯文本，输出按学科分组的文本语料。

支持 docx / doc / pdf / pptx / xlsx：
  - docx: python-docx 优先，失败后直读 zip 内 word/document.xml（兼容 CRC 损坏与文本框），再失败回退 LibreOffice；
  - pdf : pymupdf 取文本层；文本稀疏时优先采用同名 (OCR) 孪生文件，或 --ocr 走 tesseract；
  - pptx: 直读 ppt/slides 与 notesSlides 的 a:t；
  - xlsx: openpyxl 逐工作表展开。

用法:
  python3 extract.py --src /path/to/src --work /path/to/work [--ocr]

参数:
  --src   素材根目录，其下每个子目录视为一个「学科」 (默认: $KP_SRC 或 ./src)
  --work  工作目录 (默认: $KP_WORK 或 .)
  --ocr   对无文本层扫描件 PDF 执行 tesseract OCR（耗时；默认只标记 needs_ocr）

输出:
  <work>/extracted/<学科>/<NNN>__<安全名>.txt  每个源文件一份文本（首两行为来源注释）
  <work>/extracted/<学科>/manifest.json        每文件: 路径/MD5/页或段数/字符数/状态/OCR需求
"""
import os, re, sys, json, hashlib, subprocess, tempfile, shutil, glob, zipfile, argparse
from xml.etree import ElementTree as ET


def parse_args():
    ap = argparse.ArgumentParser(description='多格式素材文本提取')
    ap.add_argument('--src', default=os.environ.get('KP_SRC', 'src'), help='素材根目录（子目录=学科）')
    ap.add_argument('--work', default=os.environ.get('KP_WORK', '.'), help='工作目录')
    ap.add_argument('--ocr', action='store_true', help='对扫描件 PDF 执行 tesseract OCR')
    ap.add_argument('--ocr-lang', default='chi_sim+eng', help='tesseract 语言包')
    return ap.parse_args()


ARGS = parse_args()
SRC_ROOT = os.path.abspath(ARGS.src)
WORK = os.path.abspath(ARGS.work)
EXTRACTED = os.path.join(WORK, 'extracted')
DO_OCR = ARGS.ocr

LO = next((p for p in ['/opt/libreoffice26.8/program/soffice', '/opt/libreoffice/program/soffice']
           if os.path.exists(p)), None) or next((p for p in glob.glob('/opt/libreoffice*/program/soffice')), 'soffice')
LO_PROFILE = tempfile.mkdtemp(prefix='lo_extract_')
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def sha1(s):
    return hashlib.sha1(s.encode('utf-8')).hexdigest()


def norm_text(t):
    t = t.replace('\r\n', '\n').replace('\r', '\n')
    t = re.sub(r'[ \t\u3000]+', ' ', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()


def safe_name(name):
    n = re.sub(r'[\\/:*?"<>|]', '_', name)
    return n[:80]


def raw_docx_text(path):
    """绕过 python-docx，直接从 zip 读 word/document.xml，兼容 CRC 损坏与文本框。"""
    out = []
    try:
        zf = zipfile.ZipFile(path)
    except Exception:
        return ''
    with zf as z:
        names = [n for n in z.namelist() if re.match(r'word/(document|header\d*|footer\d*)\.xml$', n)]
        for n in sorted(names):
            try:
                data = z.read(n)
            except Exception:
                continue
            try:
                root = ET.fromstring(data)
            except Exception:
                continue
            for p in root.iter(W + 'p'):
                line = ''.join(t.text or '' for t in p.iter(W + 't'))
                if line.strip():
                    out.append(line)
    return '\n'.join(out)


def extract_docx(path):
    import docx
    try:
        d = docx.Document(path)
        lines = [p.text for p in d.paragraphs]
        for tb in d.tables:
            for row in tb.rows:
                lines.append('   '.join(c.text for c in row.cells))
        text = '\n'.join(lines)
        if text.strip():
            return text, len(d.paragraphs)
    except Exception:
        pass
    text = raw_docx_text(path)
    if text.strip():
        return text, text.count('\n') + 1
    try:
        text = lo_convert_to_txt(path)
        if text.strip():
            return text, text.count('\n') + 1
    except Exception:
        pass
    return '', 0


def extract_pptx(path):
    """pptx 为 zip：直接解析 ppt/slides/*.xml 与备注页的 a:t 文本。"""
    A = '{http://schemas.openxmlformats.org/drawingml/2006/main}t'
    out = []
    with zipfile.ZipFile(path) as z:
        names = sorted(n for n in z.namelist()
                       if re.match(r'ppt/(slides|notesSlides)/[^/]+\.xml$', n))
        for n in names:
            try:
                root = ET.fromstring(z.read(n))
            except Exception:
                continue
            lines = []
            for t in root.iter(A):
                if t.text and t.text.strip():
                    lines.append(t.text.strip())
            if lines:
                tag = '备注' if 'notesSlides' in n else n.split('/')[-1].replace('.xml', '')
                out.append('=== %s ===\n%s' % (tag, '\n'.join(lines)))
    return '\n'.join(out), len(out)


def extract_pdf(path):
    import pymupdf
    d = pymupdf.open(path)
    pages = [p.get_text() for p in d]
    d.close()
    return pages, len(pages)


def lo_convert_to_txt(path):
    """LibreOffice 转 txt，返回文本（失败抛异常）。"""
    outdir = tempfile.mkdtemp(prefix='lo_out_', dir=WORK)
    try:
        r = subprocess.run([LO, '-env:UserInstallation=file://' + LO_PROFILE,
                            '--headless', '--convert-to', 'txt:Text', '--outdir', outdir, path],
                           capture_output=True, timeout=180)
        outs = glob.glob(os.path.join(outdir, '*.txt'))
        if not outs:
            raise RuntimeError('no txt output: %s %s' % (r.returncode, r.stderr[:200]))
        return open(outs[0], encoding='utf-8', errors='replace').read()
    finally:
        shutil.rmtree(outdir, ignore_errors=True)


def ocr_pdf(path):
    """tesseract 逐页 OCR 扫描件 PDF，返回文本。"""
    import pymupdf
    d = pymupdf.open(path)
    out = []
    tmpd = tempfile.mkdtemp(prefix='ocr_', dir=WORK)
    try:
        for i, page in enumerate(d):
            pix = page.get_pixmap(dpi=300)
            img = os.path.join(tmpd, 'p%04d.png' % i)
            pix.save(img)
            r = subprocess.run(['tesseract', img, 'stdout', '-l', ARGS.ocr_lang, '--psm', '3'],
                               capture_output=True, timeout=300)
            out.append('=== 第%d页 ===\n%s' % (i + 1, r.stdout.decode('utf-8', 'replace')))
            os.remove(img)
        return '\n'.join(out), len(d)
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)
        d.close()


def find_ocr_twin(path):
    """同名 (OCR) 兄弟文件。"""
    base, ext = os.path.splitext(path)
    for cand in (base + '(OCR)' + ext, base + '_OCR' + ext, base + '-OCR' + ext):
        if os.path.exists(cand):
            return cand
    return None


def process_file(path, subject, idx):
    name = os.path.basename(path)
    ext = os.path.splitext(name)[1].lower()
    rec = {'subject': subject, 'path': os.path.relpath(path, SRC_ROOT), 'name': name,
           'ext': ext, 'bytes': os.path.getsize(path), 'status': 'ok', 'note': '',
           'units': 0, 'chars': 0, 'ocr': False}
    text = ''
    try:
        if ext == '.docx':
            text, units = extract_docx(path)
            rec['units'] = units
        elif ext == '.doc':
            text = lo_convert_to_txt(path)
            rec['units'] = text.count('\n') + 1
            rec['note'] = 'LibreOffice 转换'
        elif ext == '.pdf':
            pages, npages = extract_pdf(path)
            rec['units'] = npages
            total = sum(len(p) for p in pages)
            rec['chars_raw'] = total
            if total / max(1, npages) < 20:  # 无/稀疏文本层
                twin = find_ocr_twin(path)
                if twin:
                    text = '\n'.join(extract_pdf(twin)[0])
                    rec['note'] = '采用同名 (OCR) 版本: %s' % os.path.basename(twin)
                    rec['ocr'] = True
                elif DO_OCR:
                    text, _ = ocr_pdf(path)
                    rec['note'] = '本机 tesseract OCR'
                    rec['ocr'] = True
                else:
                    rec['status'] = 'needs_ocr'
                    rec['note'] = '无文本层且未指定 --ocr'
                    text = '\n'.join(pages)
            else:
                text = '\n'.join(pages)
        elif ext == '.pptx':
            text, units = extract_pptx(path)
            rec['units'] = units
            if not text.strip():
                rec['status'] = 'empty'
                rec['note'] = '无可提取文本'
                return rec, ''
        elif ext == '.xlsx':
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            lines = []
            for ws in wb.worksheets:
                lines.append('=== 工作表: %s ===' % ws.title)
                for row in ws.iter_rows(values_only=True):
                    cells = [str(c) for c in row if c is not None and str(c).strip()]
                    if cells:
                        lines.append('   '.join(cells))
            wb.close()
            text = '\n'.join(lines)
            rec['units'] = len(lines)
        else:
            rec['status'] = 'skipped'
            rec['note'] = '不支持的扩展名'
            return rec, ''
    except Exception as e:
        rec['status'] = 'error'
        rec['note'] = '%s: %s' % (type(e).__name__, str(e)[:200])
        return rec, ''

    text = norm_text(text)
    rec['chars'] = len(text)
    if rec['status'] == 'ok' and not text:
        rec['status'] = 'empty'
    subj_dir = os.path.join(EXTRACTED, subject)
    os.makedirs(subj_dir, exist_ok=True)
    fn = '%03d__%s.txt' % (idx, safe_name(os.path.splitext(name)[0]))
    with open(os.path.join(subj_dir, fn), 'w', encoding='utf-8') as fh:
        fh.write('<!-- SOURCE: %s -->\n' % rec['path'])
        fh.write(text + '\n')
    rec['file'] = fn
    rec['sha1'] = sha1(text) if text else ''
    return rec, text


def main():
    manifest = []
    for subject in sorted(os.listdir(SRC_ROOT)):
        root = os.path.join(SRC_ROOT, subject)
        if not os.path.isdir(root):
            continue
        files = []
        for dp, dn, fns in os.walk(root):
            for fn in fns:
                files.append(os.path.join(dp, fn))
        files.sort()
        subj_dir = os.path.join(EXTRACTED, subject)
        os.makedirs(subj_dir, exist_ok=True)
        for old in glob.glob(os.path.join(subj_dir, '*.txt')):
            os.remove(old)
        idx = 0
        for path in files:
            idx += 1
            rec, _ = process_file(path, subject, idx)
            manifest.append(rec)
            print('%-8s %-58s %-9s %6d字 %s' % (subject, rec['path'][-58:], rec['status'], rec['chars'], rec['note'][:40]))
    with open(os.path.join(EXTRACTED, 'manifest.json'), 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
    ok = [m for m in manifest if m['status'] == 'ok']
    bad = [m for m in manifest if m['status'] != 'ok']
    print('\n== 总计 %d 文件: ok=%d, 异常/跳过=%d ==' % (len(manifest), len(ok), len(bad)))
    for m in bad:
        print('  [%s] %s — %s' % (m['status'], m['path'], m['note']))
    shutil.rmtree(LO_PROFILE, ignore_errors=True)


if __name__ == '__main__':
    main()
