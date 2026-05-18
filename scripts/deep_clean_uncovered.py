#!/usr/bin/env python3
"""深度清洗未覆盖词汇，去除人名地名碎片 | Deep clean uncovered words: remove names, places, fragments.

Input:  data/exports/uncovered_words.json
Output: data/exports/uncovered_words_final.json

使用 macOS 系统词典 (/usr/share/dict/words) + 手工黑名单过滤，
仅保留真正的英语实词。
"""


import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Load system dictionary
sys_dict = set()
with open("/usr/share/dict/words", encoding="utf-8") as f:
    for line in f:
        w = line.strip().lower()
        if w:
            sys_dict.add(w)
print(f"System dict: {len(sys_dict)} words")

# Load unclean list
with open(ROOT / "data/exports/uncovered_words.json", encoding="utf-8") as f:
    uncovered = json.load(f)

# Additional junk: fragments, abbreviations, names not in STOP
JUNK = {
    # Fragments / lemmatizer artifacts
    'isn','aren','wasn','weren','hadn','hasn','haven','wouldn','shouldn',
    'couldn','doesn','didn','don','wont','cant','aint','para','pas','fbr',
    'bos','physic','specie','discus','menand','dos','cod','angeles','san',
    'apps','dna','ceo','oecd','ftc','los','vcr','pct','pec',
    'nobel','alfred','wordsworth','carnegie','capuchin',
    
    # Names
    'adam','alan','anthony','arnold','benjamin','carl','gerald','nicholas',
    'osborne','andrew','richard','samuel','barbara','margaret','davidson',
    'macdonald','mcdonald','fitzgerald','hutchinson','hendricks','matthews',
    'williamson','robertson','stephenson','johnston','nicholson','stephens',
    'jefferson','franklin','hamilton','washington','lincoln','roosevelt',
    'thatcher','cameron','joseph','matthew','luke','maria','michelle',
    'julie','cynthia','virginia','carolyn','caroline','heather',
    'helen','susan','laura','diana','jane','elaine','pamela','debora',
    'joanne','peggy','joan','beverly','sherry','sharon','sandra',
    
    # Places
    'colorado','columbia','egypt','italian','german','spanish','french',
    'dutch','swedish','norwegian','danish','polish','russian','turkish',
    'arab','jewish','canadian','mexican','brazilian','americas','african',
    'asian','european','latin','oriental','british','english','chinese',
    'japanese','indian','korean','irish','scottish','welsh','australian',
    'california','texas','florida','arizona','georgia','ohio','michigan',
    'missouri','oregon','illinois','indiana','kentucky','tennessee',
    'alabama','arkansas','mississippi','louisiana','minnesota','wisconsin',
    'nebraska','kansas','oklahoma','montana','wyoming','nevada','utah',
    'hawaii','alaska','pennsylvania','maryland','delaware','connecticut',
    'massachusetts','chicago','boston','seattle','houston','dallas','denver',
    'phoenix','atlanta','philadelphia','pittsburgh','detroit','portland',
    'manhattan','brooklyn','toronto','vancouver','montreal','ottawa',
    'beijing','shanghai','tokyo','seoul','moscow','berlin','london','paris',
    'rome','madrid','lisbon','athens','cairo','sydney','brisbane','perth',
    'amsterdam','brussels','vienna','zurich','geneva','stockholm','oslo',
    'copenhagen','helsinki','istanbul','bangkok','jakarta','manila','mumbai',
    'lagos','nairobi','accra','dakar','tunis','algiers','rabat','casablanca',
    'amazon','google','facebook','microsoft','twitter','youtube','instagram',
    'linkedin','netflix','spotify','uber','airbnb','paypal','ebay',
    'walmart','target','costco','mcdonalds','starbucks','cocacola',
    'disney','warner','paramount','hollywood','silicon',
    
    # Money / units / symbols
    'euro','yen','yuan','rupee','ruble','peso','dollar',
    
    # Roman numerals & number fragments
    'iii','vii','viii','xiii','xvii','xviii','xxiii','xxvii','xxviii',
    
    # Abbreviations
    'etc','ie','eg','vs','mr','mrs','ms','dr','prof','st','ave','blvd',
    'inc','ltd','corp','co','llc','plc',
}

CLEAN = []
for w in uncovered:
    lemma = w["lemma"].lower()
    
    # Must be in system dictionary (real English word)
    if lemma not in sys_dict:
        continue
    
    if lemma in JUNK:
        continue
    
    # Too short
    if len(lemma) <= 2:
        continue
    
    # Contains digit
    if any(c.isdigit() for c in lemma):
        continue
    
    CLEAN.append(w)

removed = len(uncovered) - len(CLEAN)
print(f"Before: {len(uncovered)}")
print(f"Removed: {removed}")
print(f"After (in dict + not junk): {len(CLEAN)}")

out = ROOT / "data" / "exports" / "uncovered_words_final.json"
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    json.dump(CLEAN, f, ensure_ascii=False, indent=2)
print(f"Exported: {out}")

print(f"\n=== Top 120 ===")
for i, w in enumerate(CLEAN[:120]):
    print(f"  {i+1:3d}. {w['lemma']:24s} {w['pos']:6s} count={w['total_count']:3d}  freq={w['frequency']:.4f}")
