import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins" / "bedrock" / "scripts"
sys.path.insert(0, str(SCRIPTS))


def owner_transcript(folder: Path, *prompts: str) -> str:
    """Write a session transcript holding the owner's own messages; return its path."""
    import json

    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "transcript.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        for prompt in prompts:
            record = {"type": "user", "message": {"role": "user", "content": prompt}}
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return str(path)
