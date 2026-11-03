"""Read-only schema and provenance inventory for historical and reviewed translations."""
from __future__ import annotations
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILES=(
    "canonical_translation_v2.csv",
    "final_review_override.csv",
    "applied_translations_v2.csv",
    "docs/v2_review/source_snapshot/V2_SOL_FINAL_OVERRIDE.csv",
    "docs/v2_review/source_snapshot/BOOK_FINAL_REVIEWED.csv",
    "docs/v2_review/MASTER_COMPARE_QUEUE_FINAL.csv",
    "docs/v2_review/BOOK_COMPARE_QUEUE_FINAL.csv",
)

def inventory(path):
    digest=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            digest.update(block)
    with path.open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"Missing header: {path}")
        cols=reader.fieldnames
        count=0; examples=[]; distinct=Counter()
        for row in reader:
            count+=1
            if len(examples)<3:
                examples.append({key:(value or "")[:100] for key,value in row.items() if key is not None})
            for key in ("record_type","field","status","review_status","source","effective_source","reviewer","mode"):
                if key in row and len(distinct)<80:
                    distinct[(key,(row[key] or "")[:50])]+=1
        return {"bytes":path.stat().st_size,"sha256":digest.hexdigest(),"rows":count,
                "columns":cols,"samples":examples,
                "common_values":{f"{k}:{v}":num for (k,v),num in distinct.most_common(40)}}

def main():
    csv.field_size_limit(100_000_000)
    report={name:inventory(ROOT/name) for name in FILES}
    path=ROOT/"docs/translation_memory/source_schema_inventory.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for name,meta in report.items():
        print(name,meta["rows"],meta["columns"])

if __name__=="__main__":
    main()
