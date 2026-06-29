# -*- coding: utf-8 -*-
"""导出对话 jsonl -> 可读 md。用户/助手文本 + 工具调用简述(结果截断)。"""
import json
SRC='/home/user1/.claude/projects/-home-user1-python-work/2b0fedbd-f1c0-463c-8183-80a145efe8a5.jsonl'
OUT='session_2b0fedbd_full.md'
def render(content):
    if isinstance(content,str): return content.strip()
    out=[]
    for b in content:
        if not isinstance(b,dict): continue
        t=b.get('type')
        if t=='text': out.append(b.get('text','').strip())
        elif t=='tool_use':
            inp=json.dumps(b.get('input',{}),ensure_ascii=False)
            out.append('`🔧 %s` %s'%(b.get('name',''), (inp[:160]+'…') if len(inp)>160 else inp))
        elif t=='tool_result':
            c=b.get('content','')
            if isinstance(c,list): c=' '.join(x.get('text','') for x in c if isinstance(x,dict))
            c=str(c).replace('\n',' ')
            out.append('`📤 result` %s'%((c[:160]+'…') if len(c)>160 else c))
    return '\n\n'.join(p for p in out if p)
n=0
with open(SRC) as f, open(OUT,'w') as o:
    o.write('# Session 2b0fedbd — 完整对话导出\n\n')
    o.write('> 低月球轨道解体碎片对地月转移轨道风险分析 (近地一次环月两次交会场景)\n\n---\n\n')
    for line in f:
        try: e=json.loads(line)
        except: continue
        msg=e.get('message',{}) or {}
        role=msg.get('role') or e.get('type','')
        if role not in ('user','assistant'): continue
        content=msg.get('content', e.get('content'))
        if content is None: continue
        body=render(content)
        if not body: continue
        tag='🧑 用户' if role=='user' else '🤖 助手'
        o.write('### %s\n\n%s\n\n'%(tag,body)); n+=1
print('[saved] %s  (%d 条消息)'%(OUT,n))
