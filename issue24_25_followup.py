"""Translate the remaining screenshot examples and their confirmed overrides."""

import re
from dataclasses import replace


PLANT_NAMES = {
    0x00025039: "용설화",
    0x000336A9: "용설화",
    0x000704A0: "암브로시아꽃",
    0x0005DCE0: "암브로시아꽃",
    0x000336B7: "드라이어드 말굽버섯",
    0x0008529D: "드라이어드 말굽버섯 갓",
    0x000336A5: "알카넷",
    0x0003365C: "알카넷 꽃",
    0x000336CC: "털까마중",
    0x00033688: "털까마중",
    0x000336C4: "황새냉이",
    0x000A7929: "황새냉이 잎",
    0x00189D1B: "골든로드",
    0x000336A2: "골든로드 씨앗 꼬투리",
}

MAGES_GUILD_RANKS = {
    "Associate": "준회원", "Apprentice": "도제", "Journeyman": "숙련자",
    "Evoker": "에보커", "Conjurer": "소환마법사", "Magician": "매지션",
    "Warlock": "워록", "Wizard": "위저드", "Master-Wizard": "마스터위저드",
    "Arch-Mage": "대마법사", "None": "없음",
}


def correct(english, korean, kind, field, formid, *, base_ids=True):
    if kind == b"BOOK" and field == b"DESC":
        return korean
    lower = english.lower()
    if field == b"FULL":
        if base_ids and kind in (b"FLOR", b"INGR") and formid in PLANT_NAMES:
            return PLANT_NAMES[formid]
        if kind == b"SPEL" and lower == "finger of the mountain":
            return "핑거즈 오브 더 마운틴"
        if kind == b"ARMO" and re.search(r"\bfur\b", lower):
            korean = korean.replace("털가죽", "모피")
        if kind == b"WEAP":
            if re.search(r"\bshort[ -]?sword\b", lower):
                korean = re.sub(r"숏\s*소드|쇼트\s*소드|짧은\s*검", "단검", korean)
            elif re.search(r"\bdagger\b", lower):
                korean = korean.replace("단검", "단도").replace("대거", "단도")
    if base_ids and kind == b"FACT" and formid == 0x00022296 and field in (b"MNAM", b"FNAM"):
        return MAGES_GUILD_RANKS.get(english, korean)
    if field == b"NAM1" and english == "The Mazken guard Crucible in New Sheoth. We ensure the Demented remain orderly and respectful of our Lord Sheogorath.":
        return "마즈켄은 뉴 셰오스의 크루시블을 지킵니다. 디멘시아 주민들이 질서를 지키고 저희의 주군 쉐오고라스를 존중하도록 살피지요."
    if "white gold tower" in lower or "white-gold tower" in lower:
        korean = re.sub(r"화이트\s*골드\s*타워|백금\s*탑", "백금 탑", korean)
    if "prince of madness" in lower:
        korean = korean.replace("광기의 왕자", "광기의 군주")
    if "chalice of reversal" in lower:
        korean = korean.replace("역행의 잔", "반전의 성배")
    if re.search(r"necromanc", lower):
        korean = korean.replace("네크로맨서", "강령술사").replace("네크로맨시", "강령술")
    return korean


def correct_table(table):
    for entries in table.values():
        for index, entry in enumerate(entries):
            text = entry.korean[:-1].decode("utf-8")
            updated = correct(entry.english, text, entry.record_type, entry.field, entry.formid)
            if updated != text:
                entries[index] = replace(entry, korean=updated.encode("utf-8") + b"\0")
