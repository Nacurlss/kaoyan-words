#!/usr/bin/env python3
"""检索墨墨词库未收录的真题词汇 | Find exam lemmas NOT in momo vocabulary + wordlists.

Input:  后端 API (/api/words) 分页获取全部词形还原索引
Output: data/exports/uncovered_words.json

对比墨墨词库、四级/高考/中考/小学词表，找出真题中出现的未覆盖单词。
"""


import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --- 1. Load known lemmas (momo + wordlists) ---
with open(ROOT / "data/processed/momo_vocab/momo_vocab.json", encoding="utf-8") as f:
    momo = json.load(f)
known = set(e["lemma"].lower() for e in momo)

# Group appendices
for fn in ["附录-基础词.json","附录-低频大纲词.json","附录-零频大纲词.json","附录-低频超纲词.json"]:
    p = ROOT / "data/processed/momo_vocab" / fn
    if p.exists():
        with open(p, encoding="utf-8") as f:
            for e in json.load(f):
                known.add(e["lemma"].lower())

# Wordlists (primary, zhongkao, gaokao, cet4)
import sys
sys.path.insert(0, str(ROOT / "src" / "backend"))
from analyzer import load_word_list
for fn in ["小学英语大纲词汇.txt", "zhongkao.txt", "gaokao.txt", "cet4.txt"]:
    p = ROOT / "src" / "backend" / "wordlists" / fn
    if p.exists():
        for w in load_word_list(str(p)):
            known.add(w.lower())

print(f"Known lemmas: {len(known)}")

# --- 2. Name/place filters ---
STOP = {
    "john","mary","james","robert","david","william","thomas","charles",
    "michael","george","edward","peter","paul","sarah","elizabeth","smith",
    "jones","brown","wilson","taylor","anderson","harris","martin","white",
    "clark","lewis","walker","hall","allen","king","wright","scott","green",
    "baker","adams","nelson","hill","ramirez","campbell","mitchell","roberts",
    "carter","phillips","evans","turner","torres","parker","collins","edwards",
    "stewart","flores","morris","nguyen","murphy","rivera","cooper","reed",
    "bailey","bell","gomez","kelly","howard","ward","cox","diaz","richardson",
    "wood","watson","brooks","bennett","gray","reyes","cruz","hughes","price",
    "myers","long","foster","sanders","ross","powell","sullivan","russell",
    "ortiz","jenkins","gutierrez","perry","butler","barnes","fisher","coleman",
    "jordan","reynolds","hamilton","graham","kim","alexander","ramos","wallace",
    "griffin","west","cole","hayes","gibson","bryant","ellis","stevens",
    "murray","ford","marshall","owens","harrison","ruiz","kennedy","wells",
    "alvarez","woods","webb","tucker","freeman","burns","henry","vasquez",
    "snyder","simpson","porter","hunter","gordon","mendez","silva","shaw",
    "holmes","rice","liu","miller","weaver","jennings","schneider","hoffman",
    "schmidt","wagner","fischer","friedman","rubin","jacobs","fox","ryan",
    "rose","bowman","lane","burke","bush","obama","truman","nixon","reagan",
    "clinton","blair","churchill","poland","brazil","anne","kate","joan","jane",
    "alice","judith","margaret","dorothy","frances","louise","marie","anita",
    "diana","samantha","amanda","melissa","jennifer","stephanie","heather",
    "nicole","jessica","angela","rachel","rebecca","deborah","julie","cynthia",
    "katherine","virginia","janet","cheryl","janice","joyce","judy","shirley",
    "jean","kathryn","amy","ann","marilyn","gloria","teresa","kathleen","andrea",
    "christine","marion","michelle","lisa","nancy","karen","betty","helen",
    "sandra","donna","carol","ruth","sharon","laura","maria","jose","carlos",
    "luis","juan","miguel","jorge","pedro","ricardo","fernando","daniel",
    "antonio","oscar","javier","alejandro","diego","pablo","manuel","patel",
    "singh","kumar","sharma","lee","chen","wang","zhang","america","europe",
    "africa","asia","australia","china","japan","korea","india","russia",
    "canada","mexico","brazil","france","germany","italy","spain","england",
    "britain","london","paris","berlin","rome","moscow","tokyo","washington",
    "york","chicago","boston","california","texas","florida","arizona",
    "michigan","georgia","ohio","missouri","harvard","yale","princeton",
    "stanford","oxford","cambridge","mit","hollywood","silicon","brooklyn",
    "manhattan","seattle","portland","denver","detroit","phoenix","hawaii",
    "alaska","iowa","kansas","kentucky","louisiana","maryland","minnesota",
    "mississippi","montana","nebraska","nevada","oregon","tennessee","utah",
    "wisconsin","wyoming","alabama","arkansas","connecticut","delaware",
    "indiana","atlanta","dallas","houston","philadelphia","pittsburgh",
    "amsterdam","brussels","stockholm","oslo","copenhagen","helsinki","venice",
    "vienna","zurich","geneva","madrid","barcelona","lisbon","athens","istanbul",
    "cairo","nairobi","lagos","sydney","melbourne","toronto","montreal",
    "vancouver","ottawa","beijing","shanghai","shenzhen","seoul","mumbai",
    "jakarta","bangkok","manila","singapore","european","american","chinese",
    "japanese","british","zealand","poland","guangzhou",
}

# --- 3. Fetch exam words from API ---
print("Fetching from API...")
all_words = []
page = 1
while True:
    url = f"http://localhost:8000/api/words?band=all&page={page}&page_size=500"
    data = json.loads(urllib.request.urlopen(url, timeout=15).read())
    batch = data["words"]
    if not batch:
        break
    all_words.extend(batch)
    if len(all_words) >= data.get("total", 0):
        break
    page += 1

print(f"Fetched {len(all_words)} exam lemmas")

# --- 4. Cross-reference ---
uncovered = []
for w in all_words:
    lemma = w["lemma"].lower()
    if lemma in known:
        continue
    if lemma in STOP:
        continue
    if len(lemma) < 3:
        continue
    pos_counts = w.get("pos_counts", {})
    top_pos = max(pos_counts, key=pos_counts.get) if pos_counts else "unknown"
    uncovered.append({
        "lemma": lemma,
        "pos": top_pos,
        "frequency": round(w.get("frequency", 0), 4),
        "total_count": sum(pos_counts.values()),
        "variants": w.get("variants", []),
    })

uncovered.sort(key=lambda x: (-x["total_count"], x["lemma"]))

print(f"\nUncovered: {len(uncovered)} words")
print(f"\n=== Top 80 ===")
for i, w in enumerate(uncovered[:80]):
    print(f"  {i+1:2d}. {w['lemma']:22s} {w['pos']:6s} count={w['total_count']:3d}  freq={w['frequency']:.4f}")

# --- 5. Export ---
out = ROOT / "data" / "exports" / "uncovered_words.json"
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    json.dump(uncovered, f, ensure_ascii=False, indent=2)
print(f"\nExported {len(uncovered)} words → {out}")
