import re, sys, bisect
L = open('bms_full.il', encoding='utf-8', errors='replace').read().split('\n')
ins_re = re.compile(r'^\s*IL_([0-9a-f]{4}):\s+(\S+)\s*(.*)$')
methods = []  # (name, [(op,arg)])
cur = None
for i, l in enumerate(L):
    s = l.strip()
    if s.startswith('.method'):
        sig = ' '.join(x.strip() for x in L[i:i+4])
        m = re.search(r'default\s+(?:\S+\s+)?(\S+)\s*\(', sig)
        cur = [m.group(1) if m else '?', []]
        methods.append(cur)
        continue
    m = ins_re.match(l)
    if m and cur is not None:
        cur[1].append((m.group(2), m.group(3).strip()))

def const(op, a):
    if op.startswith('ldc.i4.') and op[7:].isdigit(): return int(op[7:])
    if op == 'ldc.i4.m1': return -1
    if op in ('ldc.i4.s', 'ldc.i4'):
        return int(a, 0)
    return None

def fld(a):
    return a.split('::')[-1]

def describe(seq):
    if len(seq) == 1:
        c = const(*seq[0])
        if c is not None: return c & 0xff
    out = []
    for op, a in seq:
        c = const(op, a)
        if c is not None: out.append(str(c))
        elif op == 'ldfld': out.append(fld(a))
        elif op.startswith('call'):
            n = a.split('::')[-1].split('(')[0]
            out.append(n)
        elif op in ('add', 'sub', 'mul', 'div', 'and', 'or', 'xor', 'shr', 'shl'): out.append(op)
    return '{' + ' '.join(out) + '}'

res = []
for name, ins in methods:
    arrs = {}      # local -> {idx: val}
    size = {}
    i = 0
    n = len(ins)
    while i < n:
        op, a = ins[i]
        c = const(op, a)
        # newarr byte
        if c is not None and i + 2 < n and ins[i+1][0] == 'newarr' and 'Byte' in ins[i+1][1] and ins[i+2][0].startswith('stloc'):
            loc = ins[i+2][0] if '.' in ins[i+2][0] else ins[i+2][1]
            loc = ins[i+2][0].replace('stloc.', '') if '.' in ins[i+2][0] and not ins[i+2][0].endswith('.s') else ins[i+2][1]
            arrs[loc] = {}
            size[loc] = c
            i += 3; continue
        # ldloc X ; <idx const> ; <value...> ; stelem.i1
        if op.startswith('ldloc') and not op.startswith('ldloca'):
            loc = op.replace('ldloc.', '') if op not in ('ldloc.s', 'ldloc') else a
            if loc in arrs and i + 1 < n:
                ic = const(*ins[i+1])
                if ic is not None:
                    j = i + 2
                    while j < n and ins[j][0] != 'stelem.i1' and j - i < 40:
                        if ins[j][0] in ('br', 'br.s', 'brtrue.s', 'brfalse.s', 'ret', 'leave'): break
                        j += 1
                    if j < n and ins[j][0] == 'stelem.i1':
                        arrs[loc][ic] = describe(ins[i+2:j])
                        i += 1; continue
        # call check : ldarg.0 ; ldloc X ; ldc len ; call check
        if op == 'call' and 'Form1::check(' in a and i >= 3:
            lop, la = ins[i-2]
            loc = lop.replace('ldloc.', '') if lop not in ('ldloc.s', 'ldloc') else la
            ln = const(*ins[i-1])
            if loc in arrs:
                res.append((name, size.get(loc), ln, dict(arrs[loc])))
        i += 1

def fmt(v): return '%02x' % v if isinstance(v, int) else v
seen = {}
for name, sz, ln, d in res:
    mx = max(d) + 1 if d else 0
    row = ' '.join(fmt(d.get(k, '??')) for k in range(mx))
    seen.setdefault((name, row, ln), 0)
    seen[(name, row, ln)] += 1
for (name, row, ln), c in seen.items():
    print('%-28s len=%s  %s' % (name, ln, row))
print(len(res), 'chiamate,', len(seen), 'frame distinti', file=sys.stderr)
