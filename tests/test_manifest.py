import json
from pathlib import Path


def test_pair_split_is_disjoint():
    manifest = json.loads((Path(__file__).parents[1] / "evaluation/manifest.json").read_text())
    families = {}
    for item in manifest["documents"]:
        families.setdefault(item["family"], set()).add(item["split"])
    assert all(len(splits) == 1 for splits in families.values())
    assert sum(splits == {"dev"} for splits in families.values()) == 4
    assert sum(splits == {"test"} for splits in families.values()) == 2
    assert len(manifest["documents"]) == 12
