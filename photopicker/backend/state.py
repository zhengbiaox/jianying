import json
from pathlib import Path
from photopicker.backend.models import SessionState

STATE_FILENAME = ".photopicker_state.json"


def save_session(state: SessionState, folder: str) -> None:
    p = Path(folder) / STATE_FILENAME
    data = state.to_dict()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def load_session(folder: str) -> SessionState | None:
    p = Path(folder) / STATE_FILENAME
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return SessionState.from_dict(data)
    except Exception:
        return None


def delete_session(folder: str) -> None:
    p = Path(folder) / STATE_FILENAME
    if p.exists():
        p.unlink()
