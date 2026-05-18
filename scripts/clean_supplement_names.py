"""Regenerate momo_supplement.json with proper noun filtering + whitelist.

Reads from: data/processed/vocab_translations/ + data/exports/uncovered_words_final.json
Filters out proper nouns using system dictionary + manual blacklist
Keeps legitimate words via WHITELIST

Usage: python scripts/clean_supplement_names.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DICT_PATH = "/usr/share/dict/words"
CACHE_DIR = ROOT / "data/processed" / "vocab_translations"
FINAL_PATH = ROOT / "data" / "exports" / "uncovered_words_final.json"
SUPPLEMENT_PATH = ROOT / "data/processed" / "momo_vocab" / "momo_supplement.json"
UNCOVERED_TRANSLATED_PATH = ROOT / "data" / "exports" / "uncovered_words_translated.json"

MANUAL_BLACKLIST = {
    "adeline", "adrian", "austin", "betsy", "brent", "eric", "francisco",
    "greg", "jack", "oliver", "roman", "blair", "carl", "anthony", "arnold",
    "benjamin", "gerald", "nicholas", "osborne", "andrew", "richard",
    "samuel", "stephen", "albert", "stephanie", "greek", "italian",
    "french", "spanish", "german", "russian", "chinese", "japanese",
    "canadian", "mexican", "brazilian", "indian", "african", "asian",
    "european", "american", "british", "irish", "scottish", "australian",
    "columbia", "massachusetts", "california", "alabama", "arkansas",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "illinois",
    "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "michigan", "minnesota", "mississippi", "missouri",
    "montana", "nebraska", "nevada", "ohio", "oklahoma", "oregon",
    "pennsylvania", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "wisconsin", "wyoming", "colorado", "arizona",
    "seattle", "boston", "chicago", "houston", "dallas", "denver",
    "atlanta", "phoenix", "detroit", "portland", "philadelphia",
    "pittsburgh", "manhattan", "brooklyn", "paris", "london", "berlin",
    "rome", "moscow", "tokyo", "beijing", "shanghai", "toronto",
    "vancouver", "montreal", "sydney", "melbourne", "amsterdam",
    "brussels", "vienna", "zurich", "geneva", "stockholm", "oslo",
    "copenhagen", "helsinki", "madrid", "barcelona", "lisbon", "athens",
    "istanbul", "cairo", "lagos", "nairobi", "seoul", "mumbai", "jakarta",
    "bangkok", "manila", "singapore", "ottawa", "diego", "angeles",
    "wordsworth", "darwin", "newton", "einstein", "galileo", "marx",
    "freud", "shakespeare", "mozart", "beethoven", "picasso", "monet",
    "warhol", "dickens", "hemingway", "twain", "nobel", "carnegie",
    "rockefeller", "disney", "pepsi", "coke", "nike", "adidas",
    "ebay", "amazon", "facebook", "google", "microsoft", "apple",
    "twitter", "instagram", "youtube", "whatsapp", "linkedin", "netflix",
    "spotify", "uber", "airbnb", "paypal", "homer",
    "adam", "alan", "alex", "barbara", "ben", "bob", "carol", "chris",
    "dan", "dave", "david", "deborah", "diana", "donna", "edward",
    "elizabeth", "frank", "fred", "george", "harry", "helen", "henry",
    "james", "jane", "janet", "jeff", "jerry", "jessica", "jim", "joe",
    "john", "joseph", "judy", "karen", "kate", "kelly", "ken", "larry",
    "laura", "linda", "lisa", "margaret", "maria", "marie", "mark",
    "martin", "mary", "matt", "michael", "michelle", "mike", "nancy",
    "nick", "pamela", "patricia", "paul", "peter", "phil", "ralph",
    "ray", "rebecca", "rob", "robert", "ron", "rose", "ruth", "sam",
    "sandra", "sarah", "scott", "sharon", "steve", "susan", "ted",
    "thomas", "tim", "tom", "tony", "victor", "vincent", "william",
    "shirley", "joyce", "cynthia", "katherine", "virginia", "janice",
    "cheryl", "kathleen", "andrea", "christine", "marion", "gloria",
    "teresa", "ann", "amy", "joan", "irene", "louise", "marilyn",
    "judith", "dorothy", "frances", "martha", "alice", "mildred",
    "theresa", "phyllis", "bonnie", "paula", "gladys", "norma", "patty",
    "sally", "joanne", "peggy", "beverly", "sherry", "elaine", "carolyn",
    "caroline", "heather", "nicole", "melissa", "jennifer", "amanda",
    "samantha", "rachel", "angela", "anita", "doreen", "antoinette",
    "bernadette", "bridget", "cecilia", "constance", "danielle",
    "eileen", "gabrielle", "jacqueline", "josephine", "kathryn",
    "lillian", "marcella", "maureen", "patrice", "roberta", "rosemary",
    "suzanne", "thelma", "valerie", "yvonne", "victorian",
    "englishman", "frenchman", "dutchman", "irishman", "hawaiian",
    "scandinavian", "polynesian", "iberian", "hispanic", "chicano",
    "aramaic", "arabic", "aztec", "buddhist", "puritan", "populism",
    "olympia", "olympian", "vegan",
}

WHITELIST = {
    "fauna", "populist", "minimalist", "zen", "stan",
    "max", "mayo", "rosemary", "victor", "rose", "bob",
    "harry", "nick", "sally", "tony", "twain", "bonnie",
    "arabic", "aztec", "puritan", "olympia", "olympian",
    "hispanic", "aramaic", "buddhist", "vegan", "chicano",
    "hawaiian", "scandinavian", "polynesian", "iberian",
    "populism", "victorian", "dutchman", "irishman",
    "frenchman", "englishman", "czech", "slovak", "swede",
    "dane", "finn", "briton", "norman",
}


def load_proper_only() -> set:
    proper_only = set()
    common_words = set()
    with open(DICT_PATH, encoding="utf-8") as f:
        for line in f:
            orig = line.strip()
            w = orig.lower()
            if len(w) <= 1:
                continue
            if orig[0].isupper() and orig[1:].islower():
                proper_only.add(w)
            elif orig.islower():
                common_words.add(w)
    return proper_only - common_words


def main():
    pure_proper = load_proper_only()
    print(f"Dictionary proper-only: {len(pure_proper)}")

    # Read all cached translations
    all_translations = {}
    for cf in CACHE_DIR.glob("*.json"):
        all_translations.update(json.loads(cf.read_text(encoding="utf-8")))
    print(f"Cached translations: {len(all_translations)}")

    # Read final uncovered words for frequency/pos data
    with open(FINAL_PATH, encoding="utf-8") as f:
        final_words = json.load(f)
    print(f"Final words: {len(final_words)}")

    # Build supplement: only keep words that have translations AND are not proper nouns
    entries = []
    removed = []
    kept_count = 0

    for w in final_words:
        lemma = w["lemma"].lower()
        translation = all_translations.get(w["lemma"], all_translations.get(lemma, ""))
        if not translation or "|" not in translation:
            continue

        # Filter logic: WHITELIST overrides everything
        is_junk = False
        if lemma in WHITELIST:
            is_junk = False
        elif lemma in MANUAL_BLACKLIST:
            is_junk = True
        elif lemma in pure_proper:
            is_junk = True

        if is_junk:
            removed.append((lemma, translation))
            continue

        pos_raw, meaning = translation.split("|", 1)
        pos = pos_raw.strip()
        meaning = meaning.strip()
        if not meaning:
            continue

        entries.append({
            "lemma": w["lemma"],
            "group": "supplement",
            "group_idx": 0,
            "group_title": "真题补充词汇",
            "senses": [{"pos": pos, "meaning": meaning}],
            "examples_en": [],
        })
        kept_count += 1

    entries.sort(key=lambda e: e["lemma"])

    print(f"\nAfter filtering: {len(entries)}")
    print(f"Removed (proper nouns): {len(removed)}")

    # Count how many whitelisted words were in the supplement
    wl_hit = {w for w in WHITELIST if any(e["lemma"].lower() == w for e in entries)}
    print(f"Whitelisted words kept: {len(wl_hit)}")

    with open(SUPPLEMENT_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"Saved: {SUPPLEMENT_PATH}")

    # Also update uncovered_words_translated.json
    removed_lemmas = {r[0] for r in removed}
    uncovered_clean = [w for w in final_words if w["lemma"].lower() not in removed_lemmas]
    with open(UNCOVERED_TRANSLATED_PATH, "w", encoding="utf-8") as f:
        json.dump(uncovered_clean, f, ensure_ascii=False, indent=2)
    print(f"Cleaned uncovered_translated: {len(final_words)} → {len(uncovered_clean)}")

    print(f"\nRemoved items:")
    for lemma, meaning in sorted(removed, key=lambda x: x[0])[:30]:
        print(f"  {lemma:24s} → {meaning}")
    if len(removed) > 30:
        print(f"  ... and {len(removed) - 30} more")


if __name__ == "__main__":
    main()
