from enum import Enum
from pydantic import BaseModel
from typing import Optional

class PhotoGrade(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

class FilterLevel(int, Enum):
    STRICT = 80
    BALANCED = 60
    LENIENT = 40

class PhotoInfo(BaseModel):
    id: str
    path: str
    raw_path: Optional[str] = None
    xmp_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    score: int = 0
    grade: PhotoGrade = PhotoGrade.RED
    scene_group: Optional[str] = None
    is_selected: bool = False
    is_rejected: bool = False
    aesthetic_score: int = 0
    reasons: list[str] = []

class SceneGroup(BaseModel):
    id: str
    photos: list[str]
    cover_photo_id: str

class PKResult(BaseModel):
    winner_id: str
    loser_id: str

class ExportRequest(BaseModel):
    photo_ids: list[str]
    output_dir: str
    folder_name: str

class RejectionReason(str, Enum):
    BLURRY = "blurry"
    OVEREXPOSED = "overexposed"
    UNDEREXPOSED = "underexposed"
    CLOSED_EYES = "closed_eyes"
    SHAKE = "shake"
    LOW_QUALITY = "low_quality"

class GroupState(BaseModel):
    id: str
    images: list[str]
    pending: list[str] = []
    left: Optional[str] = None
    right: Optional[str] = None
    losers: list[str] = []
    winner: Optional[str] = None
    extra_winners: list[str] = []
    finished: bool = False
    auto_rejected: list[str] = []
    auto_reject_reasons: dict[str, str] = {}
    auto_selected: bool = False
    undo_stack: list[dict] = []

    def save_snapshot(self):
        self.undo_stack.append({
            "left": self.left,
            "right": self.right,
            "pending": list(self.pending),
            "losers": list(self.losers),
            "winner": self.winner,
            "extra_winners": list(self.extra_winners),
            "finished": self.finished,
        })

    def undo(self):
        if not self.undo_stack:
            return
        snap = self.undo_stack.pop()
        self.left = snap["left"]
        self.right = snap["right"]
        self.pending = snap["pending"]
        self.losers = snap["losers"]
        self.winner = snap["winner"]
        self.extra_winners = snap["extra_winners"]
        self.finished = snap["finished"]

    def to_dict(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "GroupState":
        return cls(**data)

class SessionState(BaseModel):
    folder: str
    groups: list[GroupState] = []
    current_group: int = 0
    threshold: float = 0.75
    filter_level: int = 60
    mode: str = "copy"
    created_at: float = 0.0

    def to_dict(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        groups = [GroupState.from_dict(g) for g in data.get("groups", [])]
        data["groups"] = groups
        return cls(**data)
