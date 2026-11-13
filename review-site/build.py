"""검수 사이트 빌드: review-site/index.src.html 에 데이터를 넣어 dist/index.html 을 만든다.

사용:
  python3 review-site/build.py [--review-items PATH] [--out PATH]

- v1: dataset/tool-choice-v1.labeled.jsonl (Opus 라벨 3,141건) + dataset/tool-choice-v1.gold.jsonl (시험셋 350건, 라벨 없음)
- v2 추가분: 검수용 review-items.jsonl (심은 오답이 섞인 456건, 정답표 필드 없음).
  공개 저장소에 두지 않는다. 기본 경로는 프로젝트 파일 /mnt/project-files/tool-call-grader/review-v2add/review-items.jsonl
  파일이 없으면 v1만으로 빌드한다.
- 클래스: tools-v2.json 20개. 라벨은 이름으로 읽어 인덱스로 바꾼다.
- 출력 dist/index.html 에는 심은 오답 라벨이 그대로 들어가므로 커밋하지 않는다(.gitignore).
"""
import argparse, json, random, re, collections, os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
HERE=ROOT+'review-site/'
ap=argparse.ArgumentParser()
ap.add_argument('--review-items', default='/mnt/project-files/tool-call-grader/review-v2add/review-items.jsonl')
ap.add_argument('--out', default=HERE+'dist/index.html')
A=ap.parse_args()
L=lambda p:[json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]
tools=json.load(open(ROOT+'tools-v2.json', encoding='utf-8'))['classes']
C=[t['id'] for t in tools]; ci={c:i for i,c in enumerate(C)}
v1=L(ROOT+'dataset/tool-choice-v1.labeled.jsonl')
v2=L(A.review_items) if os.path.exists(A.review_items) else []
if not v2: print('v2 검수 파일 없음: v1만 빌드')
assert not any('planted' in x or 'true_label' in x or 'control' in x for x in v2), '정답표 필드가 있는 파일은 넣지 않는다 (review-items.jsonl 을 쓸 것)'
gold=L(ROOT+'dataset/tool-choice-v1.gold.jsonl')
hp=ROOT+'dataset/tool-choice-v2add.holdout.jsonl'
holdout={x['request'] for x in (L(hp) if os.path.exists(hp) else [])}|{x['request'] for x in gold}
def issue(lb):
    s={lb['first'],*lb.get('also_ok',[])}; out=[]
    if {'ssh','none'}<=s: out.append(1)
    if {'web_search','none'}<=s: out.append(2)
    if {'server_status','ssh'}<=s: out.append(3)
    return out
v1.sort(key=lambda x:(x['cmp']['priority'], x['label'].get('confidence',1), x['id']))
rows=[]
for i,x in enumerate(v1):
    rows.append((i/len(v1), x, x['cmp']['priority'], x['cmp'].get('why',''), "ABC"[i%3]))
rnd=random.Random(20261113); k=0
for x in v2:
    if x['audience']=='all': who='*'
    else: who="ABC"[k%3]; k+=1
    rows.append((rnd.random(), x, x.get('priority',4), x.get('priority_why',''), who))
rows.sort(key=lambda r:r[0])
items=[]
for _,x,pri,why,who in rows:
    lb=x['label']
    items.append([x['id'],x['split'][0],x['lang'],x.get('context',''),x['request'],ci[lb['first']],[ci[a] for a in lb.get('also_ok',[])],[ci[a] for a in lb.get('sequence',[])],1 if lb.get('needs_confirm') else 0,lb.get('rule') or 0,lb.get('confidence',1),lb.get('note',''),pri,why,issue(lb),who])
EASY={
 "weather":"지금 날씨나 며칠 뒤 예보를 조회해요","calendar_list":"내 캘린더 일정을 읽어 와요 (빈 시간 찾기 포함)","calendar_create":"캘린더에 일정을 넣거나 바꾸거나 지워요",
 "web_search":"인터넷 검색이에요 (뉴스, 가격, 최신 정보)","map_search":"지도 검색이에요 (장소, 주변 가게, 길찾기, 거리)","fx":"지금 환율을 보거나 금액을 환산해요",
 "mail_read":"받은 메일을 읽기만 해요 (보내기는 못 해요)","server_status":"서버가 켜져 있는지, 디스크·CPU 사용량 같은 정해진 상태만 확인해요","ssh":"서버에 접속해 아무 명령이나 실행해요 (로그 보기, 재시작, 설치)",
 "memory":"사용자에 대한 사실·선호를 다음 대화에서도 쓰도록 저장·수정·삭제해요","session_search":"예전 대화에서 나눈 내용을 찾아요","cronjob":"정해진 시각·주기에 할 일을 예약해요 (알람, 타이머, 리마인더, 매일 브리핑)",
 "file":"Hermes가 도는 컴퓨터의 파일을 읽고 쓰고 찾아요","web_extract":"주어진 URL의 웹 페이지·PDF를 읽어요","browser":"브라우저로 사이트에서 클릭·입력·로그인 같은 조작을 해요",
 "execute_code":"코드를 돌려 정확히 계산하거나 데이터를 집계해요","image_generate":"그림·로고를 새로 만들거나 이미지를 고쳐요","vision_analyze":"주어진 이미지를 보고 내용을 읽거나 설명해요",
 "text_to_speech":"글을 음성으로 만들어요","none":"도구 없이 말로만 답해요 (설명·잡담, 못 하는 일, 되묻기)"}
EX1={"weather": {"yes": ["오늘 서울 날씨 어때?", "내일 비 와?", "What's the weather like in Busan this weekend?"], "no": [["어제 서울 날씨 어땠어?", "web_search"], ["날씨 앱 추천해줘", "web_search"]]}, "calendar_list": {"yes": ["이번 주 금요일 일정 뭐 있어?", "다음 주 화요일 오후 비어?", "내일 일정 시간순으로 알려줘"], "no": [["캘린더가 뭐야?", "none"]]}, "calendar_create": {"yes": ["내일 오후 3시에 치과 캘박해줘", "Add a team sync on Monday at 10am.", "tomorrow 일정 add 해줘, 오후 2시 dentist"], "no": [["메일로 온 항공권 일정 캘린더에 넣어줘", "mail_read"]]}, "web_search": {"yes": ["RTX 5090 국내 출시 가격 찾아줘", "날씨 앱 추천해줘", "어제 서울 날씨 어땠어?"], "no": [["판교 근처 치킨집 알려줘", "map_search"], ["150달러 원화로 얼마", "fx"]]}, "map_search": {"yes": ["분당 정형외과 찾아줘", "강남 세무서 전화번호", "How far is it from Gangnam station to Seoul station by subway?"], "no": []}, "fx": {"yes": ["Convert 50,000 yen to won.", "엔화로 30만 원이면 얼마고, 오사카 숙소 하루 평균이 얼마쯤이야?", "1 USD 몇 원?"], "no": [["달러 내년에 오를까?", "web_search"], ["환율이 뭐야? 쉽게 설명해줘", "none"]]}, "mail_read": {"yes": ["오늘 온 메일 중에 중요한 거 있어?", "김 교수님이 보낸 메일 답장 써줘", "메일로 온 항공권 일정 캘린더에 넣어줘"], "no": [["김 교수님한테 회의 미룬다고 메일 보내줘", "none"]]}, "server_status": {"yes": ["pve-epyc 지금 살아 있어?", "Is the backup job on HERO healthy?", "pve03 재부팅 해도 돼?"], "no": [["HERO 디스크 왜 이렇게 찼는지 봐줘", "ssh"], ["서버 상태 모니터링은 어떻게 하는 게 좋아?", "none"]]}, "ssh": {"yes": ["pve02에서 nginx 재시작해줘", "HERO 디스크 왜 이렇게 찼는지 봐줘", "Delete all old logs on pve01."], "no": [["pve03 재부팅 해도 돼?", "server_status"], ["ssh 키 만드는 법 알려줘", "none"]]}, "none": {"yes": ["안녕! 좋은 아침", "What does DNS stand for?", "캘린더가 뭐야?"], "no": [["거기 날씨는? (앞 대화: 다음 달에 오사카 가)", "weather"]]}}
ex1=EX1  # 기준서 v1 예시(seed-examples.jsonl, 시험셋 문장 제외)
YES2=collections.defaultdict(list)
for x in L(ROOT+'seed-examples-v2.jsonl'):
    if x['context'] or x['request'] in holdout: continue
    YES2[x['label']['first']].append(x['request'])
NO2={"memory":[("오늘만 나를 대장이라고 불러","none")],"session_search":[("방금 말한 첫 번째 게 뭐라고? (앞 대화에 답이 있음)","none")],
 "cronjob":[("매주 목요일 7시 스터디를 캘린더에 반복으로 넣어줘","calendar_create")],"file":[("nas01의 /etc/exports 보여줘","ssh")],
 "web_extract":[("증류 관련 글 찾아서 읽고 요약해줘","web_search")],"browser":[("미용실 예약해줘","none")],
 "execute_code":[("What's 20 percent of 50","none"),("리스트 뒤집는 파이썬 코드 써줘","none")],"image_generate":[],
 "vision_analyze":[("What does this photo show? (이미지 없음)","none")],"text_to_speech":[("오늘 일정 음성 메시지로 알려줘","calendar_list")]}
ex={}
for c in C:
    if c in ex1 and c!='none': ex[c]=ex1[c]
    else: ex[c]={"yes":(YES2.get(c,[]) if c!='none' else ex1['none']['yes'])[:3],"no":NO2.get(c, ex1.get(c,{}).get('no',[]))}
for c in ex:
    for r in ex[c]['yes']+[n[0] for n in ex[c]['no']]: assert r.split(' (')[0] not in holdout, r
T=[[t['id'],t['name_ko'],t['when'],t['not_when'],t['risk'],EASY[t['id']],ex[t['id']]['yes'],ex[t['id']]['no']] for t in tools]
# 규칙 1~12(v1) + 13~23(v2)
g1=open(ROOT+'labeling-guide.md', encoding='utf-8').read(); g2=open(ROOT+'labeling-guide-v2.md', encoding='utf-8').read()
rule=lambda txt:{int(m.group(1)):re.sub(r'[*`]','',m.group(2)).strip() for m in re.finditer(r'^(\d+)\. (.+)$',txt,re.M)}
r1={k:v for k,v in rule(g1.split('## 3.')[1].split('## 4.')[0]).items() if k<=12}
r2={k:v for k,v in rule(g2.split('## 2.')[1].split('## 3.')[0]).items() if 13<=k<=23}
R={**r1,**r2}; rules=[R[i] for i in range(1,24)]
gl=[[x['id'],x['lang'],x['context'],x['request']] for x in sorted(gold,key=lambda x:x['id'])]
d={"classes":C,"items":items,"gold":gl,"tools":T,"rules":rules}
s=json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
os.makedirs(os.path.dirname(A.out), exist_ok=True)
open(A.out,'w',encoding='utf-8').write(open(HERE+'index.src.html',encoding='utf-8').read().replace('__DATA__',s))
print('->', A.out)
print(len(items), collections.Counter(r[4] for r in rows), len(C), len(rules))
