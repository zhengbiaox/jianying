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
    thumbnail_path: Optional[str] = None
    score: int = 0
    grade: PhotoGrade = PhotoGrade.RED
    scene_group: Optional[str] = None
    is_selected: bool = False
    is_rejected: bool = False

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
