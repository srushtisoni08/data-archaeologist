import json,re,sys,csv,collections
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
raw,P,out=sys.argv[1:4]
d=json.load(open(raw,encoding='utf-8'))
L=lambda p:[json.loads(l) for l in open(P+p,encoding='utf-8')]
tr=L('/data/training/data_archaeologist_training_v1.jsonl'); ho=L('/data/evaluation/data_archaeologist_holdout_v1.jsonl')
KEYS=["finding","classification","evidence","reasoning","confidence","limitations","recommended_next_action"]
def parse(s):
    c=re.sub(r'^```\w*\n|\n```$','',s.strip())
    try: return json.loads(c)
    except: return None
def s(v):
    if isinstance(v,str): return v.strip()
    if isinstance(v,list): return " ".join(map(str,v))
    return json.dumps(v,ensure_ascii=False)
def lst(v):
    if isinstance(v,list): return [s(x) for x in v]
    if isinstance(v,dict): return [f"{k}: {s(x)}" for k,x in v.items()]
    return [v.strip()]
RISK=re.compile(r'\b(confirmed|definitely|proves?|proven|certainly|guarantee[sd]?|undoubtedly|conclusively)\b',re.I)
drop=[];keep=[];flags={}
orig_prompts={t['prompt'] for t in tr}
# near-dup within set
V=TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True).fit([r['prompt'] for r in d]); A=V.transform([r['prompt'] for r in d])
W=cosine_similarity(A);np.fill_diagonal(W,0)
dupdrop={max(i,j) for i,j in zip(*np.where(np.triu(W)>=0.9))}
for i,r in enumerate(d):
    if r['completion']:   # original 80: reviewed v1 row is the source of truth
        keep.append({"prompt":r['prompt'],"completion":r['completion'],"_src":"v1_reviewed","_i":i});continue
    if i in dupdrop: drop.append((i,"near-duplicate prompt"));continue
    j=parse(r['enhanced_completion'])
    if j is None: drop.append((i,"completion not valid JSON"));continue
    if isinstance(j,list):
        if len(j)==1 and isinstance(j[0],dict): j=j[0]
        else: drop.append((i,f"completion is list of {len(j)} findings"));continue
    if not all(k in j for k in KEYS): drop.append((i,"missing keys"));continue
    if isinstance(j['finding'],dict) or isinstance(j['reasoning'],dict): drop.append((i,"dict-typed finding/reasoning"));continue
    try: conf=float(j['confidence']); assert 0<=conf<=1
    except: drop.append((i,"bad confidence"));continue
    c={"finding":s(j['finding']),"classification":s(j['classification']),"evidence":lst(j['evidence']),
       "reasoning":s(j['reasoning']),"confidence":conf,"limitations":lst(j['limitations']),
       "recommended_next_action":s(j['recommended_next_action']),"additional_fields":{}}
    fl=[]
    if RISK.search(json.dumps(c)): fl.append("overconfident wording: "+",".join(sorted({m.group(0).lower() for m in RISK.finditer(json.dumps(c))})))
    if r['checklist_total_score']/max(1,r['checklist_max_score'])<0.8: fl.append(f"low checklist score {r['checklist_total_score']}/{r['checklist_max_score']}")
    if conf>=0.97: fl.append(f"confidence {conf}")
    if not any(x.strip() for x in c['limitations']): fl.append("empty limitations")
    if re.search(r'\b(attached|the above|as shown above)\b',r['enhanced_prompt'],re.I): fl.append("prompt may reference missing material")
    keep.append({"prompt":r['enhanced_prompt'],"completion":json.dumps(c,ensure_ascii=False),"_src":"expanded","_i":i})
    if fl: flags[len(keep)-1]=fl
with open(out+'/training_v2_clean.jsonl','w',encoding='utf-8',newline='\n') as f:
    for k in keep: f.write(json.dumps({"prompt":k['prompt'],"completion":k['completion']},ensure_ascii=False)+"\n")
with open(out+'/review_queue.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(["output_line","source_row_index","flags","prompt_start"])
    for n,fl in flags.items(): w.writerow([n+1,keep[n]['_i'],"; ".join(fl),keep[n]['prompt'][:120].replace("\n"," ")])
with open(out+'/dropped_rows.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(["source_row_index","reason"]);w.writerows(drop)
print("kept",len(keep),"(reviewed v1:",sum(k['_src']=='v1_reviewed' for k in keep),"expanded:",sum(k['_src']=='expanded' for k in keep),")")
print("dropped",len(drop),collections.Counter(r for _,r in drop))
print("flagged",len(flags)); print(collections.Counter(x.split(':')[0].split(' 0')[0] for v in flags.values() for x in v))
cs=[json.loads(k['completion'])['confidence'] for k in keep]; print("confidence mean",np.mean(cs),"share>=0.9",np.mean(np.array(cs)>=0.9))