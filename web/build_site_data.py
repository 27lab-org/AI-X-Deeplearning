"""27lab.org/tools/tool-grader/ 용 데이터 빌드.

사용:
  python web/build_site_data.py --out ../27lab-sites/sites/www/tools/tool-grader/data.json [--eval-out web/eval-index.json]

- 브라우저 안 기준선 채점기(문자 n-gram TF-IDF + kNN)가 쓸 색인을 만든다. 외부 LLM 호출 없음.
- 색인: v1 train+val (Opus 라벨) + v2 추가분 train+val (labels-v2add.jsonl).
- 시험셋(v1 gold, v2 holdout)은 넣지 않는다. 사람 3명 라벨 전이라 공개 페이지에 노출하지 않는다.
- v1과 v2 기준이 충돌하는 문장(dataset/v2add-v1-conflicts.md 의 알람·타이머 등)은 뺀다.
- --eval-out: 정확도 측정용으로 train만 색인, val을 평가셋으로 둔 파일(커밋하지 않음).
"""
import argparse, json, os, re, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--eval-out')
A = ap.parse_args()
L = lambda p: [json.loads(l) for l in open(ROOT + p, encoding='utf-8') if l.strip()]

tools = json.load(open(ROOT + 'tools-v2.json', encoding='utf-8'))
C = [c['id'] for c in tools['classes']]
ci = {c: i for i, c in enumerate(C)}

conf = open(ROOT + 'dataset/v2add-v1-conflicts.md', encoding='utf-8').read()
drop = set(re.findall(r'`(tc-[0-9a-f]{8})`', conf))

rows = []  # (split, request, context, label dict)
for x in L('dataset/tool-choice-v1.labeled.jsonl'):
    rows.append((x['split'], x['id'], x['request'], x.get('context', ''), x['label']))
lab2 = {x['id']: x for x in L('dataset/labels/labels-v2add.jsonl')}
for x in L('dataset/tool-choice-v2add.all.jsonl'):
    if x['split'] in ('train', 'val') and x['id'] in lab2:
        rows.append((x['split'], x['id'], x['request'], x.get('context', ''), lab2[x['id']]))
test = {x['request'] for x in L('dataset/tool-choice-v1.gold.jsonl')} | {x['request'] for x in L('dataset/tool-choice-v2add.holdout.jsonl')}
rows = [r for r in rows if r[1] not in drop and r[2] not in test and r[4]['first'] in ci]

def item(r):
    lb = r[4]
    return [r[2], r[3], ci[lb['first']], sorted({ci[a] for a in lb.get('also_ok', []) if a in ci} - {ci[lb['first']]}), 1 if lb.get('needs_confirm') else 0]

EN = {
 'weather': ('Weather', 'Current weather and forecast for the next few days'),
 'calendar_list': ('Calendar lookup', 'Read your calendar, find free time'),
 'calendar_create': ('Calendar create', 'Add, change or delete an event'),
 'web_search': ('Web search', 'News, prices, anything recent or unknown'),
 'map_search': ('Map search', 'Places, nearby shops, directions, travel time'),
 'fx': ('Exchange rate', 'Current rate or converting an amount'),
 'mail_read': ('Read mail', 'Check and summarize received mail (cannot send)'),
 'memory': ('Memory', 'Save a fact or preference for future chats'),
 'session_search': ('Past chats', 'Find what was said in an earlier conversation'),
 'cronjob': ('Schedule', 'Alarms, timers, reminders, recurring jobs'),
 'file': ('Local files', 'Read, write and search files on the agent machine'),
 'web_extract': ('Read a page', 'Read or summarize a given URL or PDF'),
 'browser': ('Browser', 'Click, type or log in on a named site'),
 'execute_code': ('Run code', 'Exact calculation or data aggregation'),
 'image_generate': ('Image generate', 'Create or edit an image'),
 'vision_analyze': ('Image analysis', 'Describe or read a given image'),
 'text_to_speech': ('Text to speech', 'Turn text into audio'),
 'none': ('No tool', 'Answer in words: explain, chat, refuse, or ask back'),
}
cls = [[c['id'], c['name_ko'], c['when'], c['not_when'], c['risk'], *EN[c['id']]] for c in tools['classes']]

def dump(path, items):
    d = {'v': tools['version'], 'classes': cls, 'items': items}
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, separators=(',', ':'))
    print('->', path, len(items), 'items', os.path.getsize(path) // 1024, 'KB')

dump(A.out, [item(r) for r in rows])
if A.eval_out:
    d = {'v': tools['version'], 'classes': cls, 'items': [item(r) for r in rows if r[0] == 'train'],
         'eval': [item(r) for r in rows if r[0] == 'val']}
    json.dump(d, open(A.eval_out, 'w', encoding='utf-8'), ensure_ascii=False)
    print('eval train', len(d['items']), 'val', len(d['eval']))
print(collections.Counter(C[item(r)[2]] for r in rows).most_common())
