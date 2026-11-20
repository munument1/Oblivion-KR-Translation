"""Build source-checked Ayleid Steps, Lost Spires, MOO, and OOO base corrections."""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

from build_obcjk_overlay import records
from build_unofficial_release import rewrite
from build_vanilla_overlay import sha256_file

# English and Korean plugin SHA-256, respectively.
MODS = {
    "steps": ("The Ayleid Steps.esp",
              "d5b7008e825cc5bfd7ae7d4ca86066c8e3dd51c9816d8395f665ed6a963b67d7",
              "3e4e98b0cca4c2c1dcb7c1cf796facfd53645d253b77097f06495d368f8f73c5"),
    "spires": ("The Lost Spires.esp",
               "37337bef90a92b17cacd3bc31a5c51cbb6384d601875c97e53ef83ce62b80808",
               "e242f3ddfe58bf50c1dc461afd99a08eff743c0f56cc2261f6e392528d1d9b93"),
    "moo": ("Maskar's Oblivion Overhaul.esp",
            "705bff0d1c2405bb25a2b22201741ce6412ff97d9c452a5fa71dd82e14d98297",
            "2756bdd972e6bb0802dc7a34494741f3ca09c6f79eb55bfd56e8febe05a241f1"),
    "ooo-base": ("Oscuro's_Oblivion_Overhaul.esm",
                 "17ecd3d3f3419fb7f66e923fbc1d45f6bd50acb6d9004302c58c41784efb2771",
                 "9c7aea22700cde1147b2c49ee2db2d3472fe5880587baec956739515c3e09881"),
}
RANKS = {
    "Tyro": "수습생", "Enforcer": "집행관", "Aspirant": "지원자", "Disciple": "제자",
    "Fellow": "정회원", "Expert": "전문가", "Mentor": "지도관", "Headmaster": "길드장",
}
# The original creatures share the same raw ingredients and cooking recipes.
FISH = {
    0x013A6833: ("Marlin Fillet", "청새치 살코기", "생선 살코기"),
    0x013A9174: ("Cooked Marlin Fillet", "청새치 살코기 구이", "생선 살코기 구이"),
    0x013A6839: ("Red Snapper Fillet", "붉은퉁돔 살코기", "퉁돔 살코기"),
    0x013A9172: ("Cooked Red Snapper Fillet", "붉은퉁돔 살코기 구이", "퉁돔 살코기 구이"),
}
INGREDIENTS = {
    "moo": FISH,
    "ooo-base": {0x0102F9F5: ("Mystical Imp's Gall", "신비한 임프의 쓸개", "신비한 임프의 담즙")},
}
ARCH_MAGE = re.compile(r"\bArch[ -]?Mage\b", re.I)
ARCH_MAGE_KR = re.compile(r"아치\s*메이지|아크\s*메이지|아키\s*메이지")


def shift_initials(text: str) -> str:
    return "".join(chr(0xAC00 + (ord(ch) - 0xAC00 + 588) % (19 * 588))
                   if "가" <= ch <= "힣" else ch for ch in text)


RIDDLES = {
    # Reversal, misplaced spaces, one-step shift, and scrambled words.
    "iadnilfohtronagnafotsew": "앙가서쪽린다이북쪽"[::-1],
    "is tan dat awel land be hin data tarism or a ham eisvaht ace nand then or thayle ids te pism yen trance.":
        "나 는우 물에 서있 다내 뒤로 는아 타타르, 모라하 메와 바타 켄이있 다. 북쪽 에일리 드발 판이 내입 구다.",
    "jo uif csbwjm gjhiufst hvjme cbtfnfou":
        shift_initials("브라빌 파이터 길드 지하실에 있다") + " (초성이 한 칸 밀려 있다.)",
    "thron fo wryesel bredor, hebdin ailodest lingibud, no poles.":
        "웨엘어스 계경 쪽북, 딴외 물건 편뒤, 사면경 위.",
}


def build(mod: str, english: Path, korean: Path, output: Path) -> int:
    name, english_sha, korean_sha = MODS[mod]
    if sha256_file(english) != english_sha or sha256_file(korean) != korean_sha:
        raise ValueError(f"Wrong English or Korean release of {name}")
    if output.name != name or output.exists():
        raise ValueError(f"Use a new output path ending in {name}")

    original = {key: fields for key, _, fields, _ in records(english)}
    ingredients = INGREDIENTS.get(mod, {})
    changes = defaultdict(dict)
    changed_riddles = set()
    for key, _, fields, _ in records(korean):
        kind, fid = key
        english_fields = original.get(key, ())
        for index, (tag, raw, _) in enumerate(fields):
            if index >= len(english_fields) or tag != english_fields[index][0]:
                continue
            source = english_fields[index][1]
            if mod == "steps" and (kind, tag) in ((b"BOOK", b"DESC"), (b"QUST", b"CNAM")):
                source_text = source.rstrip(b"\0").decode("cp1252")
                text = raw.rstrip(b"\0").decode("utf-8")
                target = ARCH_MAGE_KR.sub("대마법사", text) if ARCH_MAGE.search(source_text) else text
                if fid == 0x0205BA70:
                    for clue, localized in RIDDLES.items():
                        if source_text.count(clue) != 1 or text.count(clue) != 1:
                            raise ValueError("Ayleid Steps clue differs from the reviewed text")
                        target = target.replace(clue, localized, 1)
                        changed_riddles.add(clue)
            elif mod == "spires" and key == (b"FACT", 0x0102A366) and tag in (b"MNAM", b"FNAM"):
                text = raw.rstrip(b"\0").decode("utf-8")
                if source.rstrip(b"\0").decode("ascii") != text:
                    raise ValueError("Lost Spires rank differs from the reviewed text")
                target = RANKS[text]
            elif kind == b"INGR" and index == 1 and tag == b"FULL" and fid in ingredients:
                expected, text, target = ingredients[fid]
                if source != expected.encode("ascii") + b"\0" or raw != text.encode() + b"\0":
                    raise ValueError(f"Ingredient differs from the reviewed text for {name}: {fid:08X}")
            else:
                continue
            if target != text:
                changes[key][index] = (tag, raw, target.encode() + (b"\0" if raw.endswith(b"\0") else b""))

    count = sum(map(len, changes.values()))
    if (mod == "steps" and (changed_riddles != RIDDLES.keys() or count <= 1)
            or mod == "spires" and count != 2 * len(RANKS)
            or ingredients and count != len(ingredients)):
        raise ValueError(f"Incomplete correction set for {name}: {count}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as directory:
        staged = Path(directory) / name
        if rewrite(korean, staged, changes) != count:
            raise ValueError(f"Incomplete write for {name}")
        for before, after in zip(records(korean), records(staged), strict=True):
            key, header, fields, groups = before
            new_key, new_header, new_fields, new_groups = after
            if (new_key, new_header[8:], new_groups) != (key, header[8:], groups):
                raise ValueError(f"Changed record layout for {name}: {key}")
            for index, ((tag, raw, _), (new_tag, new_raw, _)) in enumerate(zip(fields, new_fields, strict=True)):
                expected = changes.get(key, {}).get(index)
                if (new_tag, new_raw) != (tag, expected[2] if expected else raw):
                    raise ValueError(f"Unexpected field change for {name}: {key} {index}")
        staged.rename(output)
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mod", choices=MODS)
    parser.add_argument("english", type=Path)
    parser.add_argument("korean", type=Path)
    parser.add_argument("output", type=Path, help="New path with the original ESP filename")
    args = parser.parse_args()
    count = build(args.mod, args.english, args.korean, args.output)
    print(f"{args.output}: {count} corrected fields verified")


if __name__ == "__main__":
    main()
