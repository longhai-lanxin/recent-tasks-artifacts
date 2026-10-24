# -*- coding: utf-8 -*-
r"""test_omml.py — latex-omml 冒烟测试：python3 test_omml.py"""
from omml import latex_to_omml

CASES = [
    (r'E_k=\frac12mv^2', ['<m:sSub>', '<m:f>', '<m:den>']),
    (r'F=k\frac{q_1q_2}{r^2}', ['<m:f>', '<m:sSub>', 'q', 'r']),
    (r'E=mc^2', ['<m:sSup>', 'E', 'm', 'c']),
    (r'v=v_0+at', ['<m:sSub>', '0']),
    (r'\vec{F}=m\vec{a}', ['<m:acc>', 'F', 'a']),
    (r'T=2\pi\sqrt{\frac{l}{g}}', ['<m:rad>', 'π']),
    (r'\lambda=\frac{h}{p}', ['λ', '<m:f>']),
    (r'k=9.0\times10^9', ['×', '<m:sSup>']),
    ('', ['']),
]


def main():
    ok = 0
    for latex, expects in CASES:
        out = latex_to_omml(latex)
        for e in expects:
            assert e in out, 'missing %r in output of %r:\n%s' % (e, latex, out)
        if latex:
            assert out.startswith('<m:oMath>') and out.endswith('</m:oMath>'), out
        ok += 1
        print('OK  %-28s -> %d chars' % (latex or '(empty)', len(out)))
    print('\n== %d/%d 通过 ==' % (ok, len(CASES)))


if __name__ == '__main__':
    main()
