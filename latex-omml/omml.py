# -*- coding: utf-8 -*-
import re
"""LaTeX -> OMML (Office Math Markup Language) converter, subset sufficient for HS physics."""

GREEK = {
 'alpha':'α','beta':'β','gamma':'γ','delta':'δ','epsilon':'ε','varepsilon':'ε','zeta':'ζ',
 'eta':'η','theta':'θ','vartheta':'ϑ','iota':'ι','kappa':'κ','lambda':'λ','mu':'μ','nu':'ν',
 'xi':'ξ','pi':'π','rho':'ρ','sigma':'σ','tau':'τ','upsilon':'υ','phi':'φ','varphi':'φ',
 'chi':'χ','psi':'ψ','omega':'ω',
 'Gamma':'Γ','Delta':'Δ','Theta':'Θ','Lambda':'Λ','Xi':'Ξ','Pi':'Π','Sigma':'Σ','Upsilon':'Υ',
 'Phi':'Φ','Psi':'Ψ','Omega':'Ω',
}
SYM = {
 'times':'×','cdot':'·','pm':'±','mp':'∓','div':'÷','le':'≤','leq':'≤','ge':'≥','geq':'≥',
 'ne':'≠','neq':'≠','approx':'≈','equiv':'≡','propto':'∝','infty':'∞','to':'→',
 'rightarrow':'→','longrightarrow':'⟶','leftarrow':'←','Rightarrow':'⇒','Leftrightarrow':'⇔',
 'leftrightarrow':'↔','sim':'∼','ll':'≪','gg':'≫','angle':'∠','perp':'⊥','parallel':'∥',
 'circ':'°','degree':'°','%':'%','int':'∫','oint':'∮','sum':'∑','prod':'∏','partial':'∂','nabla':'∇',
 'cdots':'⋯','ldots':'…','dots':'…','prime':'′','therefore':'∴','because':'∵','ast':'∗',
 'star':'⋆','oplus':'⊕','otimes':'⊗','cup':'∪','cap':'∩','in':'∈','notin':'∉','subset':'⊂',
 'forall':'∀','exists':'∃','langle':'⟨','rangle':'⟩','sqrt':'√','overbrace':None,'underbrace':None,
}
SPACES = {' ':'\u00a0','quad':'\u2003','qquad':'\u2003\u2003',',':'\u2009',';':'\u2009',':':'\u2009','!':''}
FUNCS = {'lg','ln','log','sin','cos','tan','cot','sec','csc','arcsin','arccos','arctan','exp','max','min','lim','det','mod','sgn'}
ACCENTS = {'vec':'⃗','bar':'̄','hat':'^','dot':'˙','ddot':'¨','tilde':'~','overline':'̄','underline':'_','overrightarrow':'⃗','overleftarrow':'⃖'}
TEXTCMDS = {'text','mathrm','mathbf','mathit','mathsf','mathtt','operatorname','textnormal','mbox'}

def esc(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def run(text, sty=None):
    if text=='':
        return ''
    rpr = '<m:rPr><m:sty m:val="%s"/></m:rPr>' % sty if sty else ''
    return '<m:r>%s<m:t xml:space="preserve">%s</m:t></m:r>' % (rpr, esc(text))


SUPMAP = {'0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶',
          '7':'⁷','8':'⁸','9':'⁹','-':'⁻','+':'⁺','.':'·','n':'ⁿ'}
SUBMAP = {'0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆',
          '7':'₇','8':'₈','9':'₉','-':'₋','+':'₊'}
def _scriptify(txt, m):
    return ''.join(m.get(c, c) for c in txt)

_CMDRE = re.compile(r'\\([A-Za-z]+|[^A-Za-z])')
def plain_math(txt):
    """Best-effort: turn a LaTeX snippet into readable plain text for use inside \\mathrm/\\text."""
    def repl(m):
        name = m.group(1)
        if name in GREEK: return GREEK[name]
        if name in SYM and SYM[name]: return SYM[name]
        if name in SPACES: return SPACES[name]
        if name in ('\\',' '): return ' '
        if name in ('{','}','%','_','&','#'): return name
        return name
    for _ in range(4):
        new = re.sub(r'\\frac\{([^{}]*)\}\{([^{}]*)\}', r'(\1)/(\2)', txt)
        if new == txt: break
        txt = new
    for _ in range(3):
        new = re.sub(r'\\sqrt\{([^{}]*)\}', r'√(\1)', txt)
        if new == txt: break
        txt = new
    t = _CMDRE.sub(repl, txt)
    t = re.sub(r'\\mathrm\{([^{}]*)\}', r'\1', t)
    t = re.sub(r'\^\{([^{}]*)\}', lambda m: _scriptify(m.group(1), SUPMAP), t)
    t = re.sub(r'\^([0-9n+\-.])', lambda m: _scriptify(m.group(1), SUPMAP), t)
    t = re.sub(r'_\{([^{}]*)\}', lambda m: _scriptify(m.group(1), SUBMAP), t)
    t = re.sub(r'_([0-9+\-])', lambda m: _scriptify(m.group(1), SUBMAP), t)
    t = t.replace('{','').replace('}','')
    return t

class Parser:
    def __init__(self, s):
        self.s = s; self.i = 0
    def eof(self): return self.i >= len(self.s)
    def peek(self): return self.s[self.i] if self.i < len(self.s) else ''
    def starts(self, tok): return self.s.startswith(tok, self.i)

    def parse_seq(self, stop_cmd=None):
        """Returns list of items: ('atom', xml) | ('sup', xml) | ('sub', xml)"""
        items = []
        while not self.eof():
            c = self.peek()
            if c == '}':
                break
            if stop_cmd and self.starts('\\'+stop_cmd):
                break
            if c == '{':
                self.i += 1
                inner = self.parse_seq()
                if self.peek() == '}': self.i += 1
                items.append(('atom', self.wrap_group(inner)))
            elif c == '\\':
                items.append(('atom', self.parse_cmd()))
            elif c in '^_':
                self.i += 1
                arg = self.parse_arg()
                items.append(('sup' if c=='^' else 'sub', arg))
            elif c.isspace():
                self.i += 1
            elif c.isdigit():
                j = self.i
                while j < len(self.s) and (self.s[j].isdigit() or self.s[j] == '.'):
                    j += 1
                items.append(('atom', run(self.s[self.i:j])))
                self.i = j
            else:
                self.i += 1
                items.append(('atom', run(c)))
        return items

    def wrap_group(self, items):
        return self.apply_scripts(items)

    def parse_arg(self):
        if self.peek() == '{':
            self.i += 1
            inner = self.parse_seq()
            if self.peek() == '}': self.i += 1
            return self.apply_scripts(inner)
        if self.peek() == '\\':
            return self.parse_cmd()
        c = self.peek()
        if c == '':
            return ''
        self.i += 1
        return run(c)

    def parse_until_right(self):
        return self.parse_seq(stop_cmd='right')

    def parse_cmd(self):
        self.i += 1  # backslash
        if self.eof(): return ''
        c = self.peek()
        if c.isalpha():
            j = self.i
            while j < len(self.s) and self.s[j].isalpha(): j += 1
            name = self.s[self.i:j]; self.i = j
        else:
            name = c; self.i += 1
        if name in ('frac','dfrac','tfrac'):
            num = self.parse_arg(); den = self.parse_arg()
            return '<m:f><m:num>%s</m:num><m:den>%s</m:den></m:f>' % (num, den)
        if name == 'sqrt':
            deg = ''
            if self.peek() == '[':
                self.i += 1
                inner = self.parse_seq()
                if self.peek() == ']': self.i += 1
                deg = self.apply_scripts(inner)
            body = self.parse_arg()
            if deg:
                pre = '<m:radPr><m:degHide m:val="0"/></m:radPr><m:deg>%s</m:deg>' % deg
            else:
                pre = '<m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/>'
            return '<m:rad>%s<m:e>%s</m:e></m:rad>' % (pre, body)
        if name in ACCENTS:
            body = self.parse_arg()
            ch = ACCENTS[name]
            return ('<m:acc><m:accPr><m:chr m:val="%s"/></m:accPr><m:e>%s</m:e></m:acc>'
                    % (esc(ch), body))
        if name in TEXTCMDS:
            if self.peek() == '{':
                self.i += 1
                j = self.s.find('}', self.i)
                txt = self.s[self.i:j] if j >= 0 else self.s[self.i:]
                self.i = (j+1) if j >= 0 else len(self.s)
            else:
                txt = self.parse_plain_token()
            return run(plain_math(txt), sty='p')
        if name == 'left':
            beg = self.peek(); self.i += 1
            inner = self.parse_until_right()
            if self.starts('\\right'): self.i += len('\\right')
            end = self.peek(); self.i += 1
            b = '' if beg == '.' else esc(beg)
            e = '' if end == '.' else esc(end)
            return ('<m:d><m:dPr><m:begChr m:val="%s"/><m:endChr m:val="%s"/></m:dPr><m:e>%s</m:e></m:d>'
                    % (b, e, self.apply_scripts(inner)))
        if name == 'right':
            return ''
        if name in ('begin','end'):
            # unsupported environment: emit nothing, keep scanning
            while not self.eof() and self.peek() != '}': self.i += 1
            if self.peek() == '}': self.i += 1
            return ''
        if name in SPACES:
            return run(SPACES[name])
        if name in FUNCS:
            return run(name, sty='p')
        if name in GREEK:
            return run(GREEK[name])
        if name in SYM:
            v = SYM[name]
            return run(v) if v else ''
        if name in ('overbrace','underbrace'):
            return self.parse_arg()
        # unknown command -> literal text (mark for QA)
        return run(name)

    def parse_plain_token(self):
        j = self.i
        while j < len(self.s) and not self.s[j].isspace(): j += 1
        t = self.s[self.i:j]; self.i = j
        return t

    @staticmethod
    def apply_scripts(items):
        out = []; base = None; sup = None; sub = None
        def flush():
            nonlocal base, sup, sub
            if base is None and sup is None and sub is None: return
            b = base if base is not None else run('')
            if sup is not None and sub is not None:
                out.append('<m:sSubSup><m:e>%s</m:e><m:sub>%s</m:sub><m:sup>%s</m:sup></m:sSubSup>' % (b, sub, sup))
            elif sup is not None:
                out.append('<m:sSup><m:e>%s</m:e><m:sup>%s</m:sup></m:sSup>' % (b, sup))
            elif sub is not None:
                out.append('<m:sSub><m:e>%s</m:e><m:sub>%s</m:sub></m:sSub>' % (b, sub))
            else:
                out.append(b)
            base = sup = sub = None
        for kind, val in items:
            if kind == 'atom':
                flush(); base = val
            elif kind == 'sup':
                if base is None and not out: base = run('')
                sup = val
            else:
                if base is None and not out: base = run('')
                sub = val
        flush()
        return ''.join(out)

def latex_to_omml(latex):
    """Return OMML <m:oMath>...</m:oMath> XML string, or '' if input empty."""
    s = (latex or '').strip()
    if not s: return ''
    s = s.strip('$')
    s = s.replace('\\(','').replace('\\)','').replace('\\[','').replace('\\]','')
    for a,b in (('−','-'),('×','\\times '),('·','\\cdot ')):
        pass
    try:
        items = Parser(s).parse_seq()
        body = Parser.apply_scripts(items)
    except Exception:
        body = run(s)
    return '<m:oMath>%s</m:oMath>' % body

if __name__ == '__main__':
    tests = [r'E_k=\frac12mv^2', r'F=k\frac{q_1q_2}{r^2}', r'a=\frac{qE}{m}',
             r'v=v_0+at', r'x=v_0t+\frac12at^2', r'U_{AB}=\frac{W_{AB}}{q}',
             r'E_p=q\varphi', r'\varepsilon=\frac{\Delta\Phi}{\Delta t}',
             r'm_1v_1+m_2v_2=m_1v_1\'+m_2v_2\'', r'T=2\pi\sqrt{\frac{l}{g}}',
             r'\vec{F}=m\vec{a}', r'B=\frac{F}{IL}', r'k=9.0\times10^9\,\mathrm{N\cdot m^2/C^2}',
             r'\lambda=\frac{h}{p}', r'E=mc^2', r'P=\frac{W}{t}', r'\eta=\frac{W_{有用}}{W_{总}}\times100\%']
    for t in tests:
        x = latex_to_omml(t)
        print('IN :', t)
        print('OUT:', x[:400])
        print()
