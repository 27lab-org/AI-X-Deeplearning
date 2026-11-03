"""검수 엑셀 생성. 사용: python3 build_review_sheet.py <labeled.jsonl> <gold.jsonl> <out.xlsx>
labeled.jsonl: merge_labels.py 출력(tool-choice-v1.labeled.jsonl, label+cmp 포함), gold.jsonl: 골드 문장(라벨 없음)."""
import json, sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation

CLASSES = ["weather","calendar_list","calendar_create","web_search","map_search","fx","mail_read","server_status","ssh","none"]
HEAD = PatternFill("solid", fgColor="DDE7F0"); EDIT = PatternFill("solid", fgColor="FFF6D5")

def load(p): return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

def sheet(ws, cols, widths, edit_cols):
    ws.append(cols)
    for i, c in enumerate(ws[1], 1):
        c.font = Font(bold=True); c.fill = HEAD
        ws.column_dimensions[c.column_letter].width = widths[i-1]
    ws.freeze_panes = "A2"
    return {c: cols.index(c)+1 for c in edit_cols}

def dv(ws, formula, col, n):
    d = DataValidation(type="list", formula1=formula, allow_blank=True); ws.add_data_validation(d)
    L = ws.cell(1, col).column_letter; d.add(f"{L}2:{L}{n+1}")

def main(labeled, gold, out):
    L, G = load(labeled), load(gold)
    wb = Workbook(); ws = wb.active; ws.title = "안내"
    for r in ["툴콜 도구 고르기 검수 시트 v2 (Opus 5.5 라벨, 2026-10-21)", "", "검수 시트: 강한 라벨러(Opus 5.5) 값이 맞으면 판정=OK, 틀리면 판정=수정 후 노란 칸에 고친 값, 모르겠으면 보류.",
              "우선 1=라벨러 확신 낮음, 2=생성 의도와 다름, 3=also_ok로만 일치·확인필요 불일치, 4=일치. 위에서부터 순서대로 보면 됨.",
              "골드_A/B/C: 각자 자기 시트만. 라벨러 값 없음. 서로 상의 금지.", "기준: labeling-guide.md 3절 경계 규칙. 1건 20~30초, 1분 넘으면 보류.",
              "도구 10개: " + ", ".join(CLASSES)]:
        ws.append([r])
    ws.column_dimensions["A"].width = 110; ws["A1"].font = Font(bold=True, size=14)

    # type(easy/tricky/cannot/clarify)과 생성 의도는 검수자 편향을 막기 위해 넣지 않는다. 우선(1~4)만 표시.
    cols = ["우선","우선_이유","id","split","lang","context","request","라벨_first","라벨_also_ok","라벨_sequence","라벨_확인필요","라벨_확신","라벨_note","판정","수정_first","수정_also_ok","수정_확인필요","검수자","메모"]
    ws = wb.create_sheet("검수")
    m = sheet(ws, cols, [5,14,11,6,5,28,46,15,18,26,9,7,30,8,15,18,9,8,30], ["판정","수정_first","수정_확인필요"])
    for x in L:
        lb = x.get("label", {}); cp = x.get("cmp", {})
        ws.append([cp.get("priority", ""), cp.get("why", ""), x["id"], x.get("split","train"), x["lang"], x.get("context",""), x["request"],
                   lb.get("first",""), ",".join(lb.get("also_ok",[])), " → ".join(lb.get("sequence",[])),
                   "예" if lb.get("needs_confirm") else "아니오", lb.get("confidence", ""), lb.get("note",""), "", "", "", "", "", ""])
    dv(ws, '"OK,수정,보류"', m["판정"], len(L)); dv(ws, '"'+",".join(CLASSES)+'"', m["수정_first"], len(L)); dv(ws, '"예,아니오"', m["수정_확인필요"], len(L))
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
            if c.column >= m["판정"]: c.fill = EDIT

    gcols = ["id","lang","context","request","first","also_ok","확인필요","메모"]
    for who in "ABC":
        ws = wb.create_sheet(f"골드_{who}")
        m = sheet(ws, gcols, [11,5,28,50,15,20,9,30], ["first","확인필요"])
        for x in G: ws.append([x["id"], x["lang"], x.get("context",""), x["request"], "", "", "", ""])
        dv(ws, '"'+",".join(CLASSES)+'"', m["first"], len(G)); dv(ws, '"예,아니오"', m["확인필요"], len(G))
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
                if c.column >= m["first"]: c.fill = EDIT

    ws = wb.create_sheet("도구")
    t = json.load(open("tools.json", encoding="utf-8"))
    sheet(ws, ["id","이름","언제","아닐 때","Hermes 호출","위험"], [15,12,45,45,50,12], [])
    for c in t["classes"]:
        ws.append([c["id"], c["name_ko"], c["when"], c["not_when"], c["hermes_call"], c["risk"]])
    for row in ws.iter_rows(min_row=2):
        for c in row: c.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(out)

if __name__ == "__main__":
    main(*sys.argv[1:4])
