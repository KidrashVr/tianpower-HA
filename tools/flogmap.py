import re,sys,json
L=open('bms_full.il',encoding='utf-8',errors='replace').read().split('\n')
def cint(s):
    s=s.strip(); m=re.match(r'ldc\.i4\.(\d)\s*$',s)
    if m: return int(m.group(1))
    m=re.match(r'ldc\.i4(?:\.s)?\s+(-?\w+)\s*$',re.sub(r'^\s*IL_\w+:\s+','',s))
    return int(m.group(1),0) if m else None
def op(l): return re.sub(r'^\s*IL_\w+:\s+','',l).strip()
def dec(k):
    hexs=[]
    while True:
        hexs+=re.findall(r'\b[0-9a-f]{2}\b',re.sub(r'//.*','',L[k].replace('ldstr bytearray (','')).replace(')',''))
        if ')' in L[k]: break
        k+=1
    return bytes(int(h,16) for h in hexs).decode('utf-16le','replace').replace('�','')
res=[]
i=0
while i<len(L):
    if 'ldfld' in L[i] and '::flogbuff' in L[i]:
        a=op(L[i+1]); b=op(L[i+2]); c=op(L[i+3]); d=op(L[i+4])
        idx=cint(a)
        if idx is not None and b.startswith('ldelem.u1'):
            mask=cint(c) if c.startswith('ldc') else None
            if mask is not None and d=='and':
                # look ahead for strings / targets
                en=None; cn=None; tgt=None; pic=None
                for j in range(i+5,i+120):
                    lj=L[j]
                    if 'ldfld' in lj and '::flogbuff' in lj and j>i+8: break
                    m=re.search(r'ldstr\s+"(.*)"',lj)
                    if m and en is None and m.group(1) not in ('English',''): en=m.group(1)
                    if 'ldstr bytearray' in lj and cn is None: cn=dec(j)
                    m=re.search(r"stfld string .*::(\w+)",lj)
                    if m and tgt is None: tgt=m.group(1)
                    m=re.search(r'get_(\w+)\(\)',lj)
                    if m and 'Resources' in lj and pic is None: pic=m.group(1)
                res.append((i+1,idx,mask,en,cn,tgt,pic))
    i+=1
seen=set()
for r in res:
    print('byte[%d] & 0x%02x  -> %-34s %-12s %s'%(r[1],r[2],r[3],r[5],r[4] or ''), '(line %d)'%r[0])
print(len(res),file=sys.stderr)
