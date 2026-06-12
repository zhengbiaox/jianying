from photopicker.backend.models import PhotoInfo, PhotoGrade, SceneGroup, FilterLevel

def test_photo_info_creation():
    photo = PhotoInfo(
        id="1",
        path="/photos/img001.jpg",
        raw_path="/photos/img001.ARW",
        thumbnail_path="/cache/thumb_001.jpg",
        score=85,
        grade=PhotoGrade.GREEN,
        scene_group="scene_1"
    )
    assert photo.id == "1"
    assert photo.score == 85
    assert photo.grade == PhotoGrade.GREEN

def test_photo_grade_values():
    assert PhotoGrade.GREEN.value == "green"
    assert PhotoGrade.YELLOW.value == "yellow"
    assert PhotoGrade.RED.value == "red"

def test_filter_level_thresholds():
    assert FilterLevel.STRICT.value == 80
    assert FilterLevel.BALANCED.value == 60
    assert FilterLevel.LENIENT.value == 40

def test_scene_group():
    group = SceneGroup(
        id="scene_1",
        photos=["1", "2", "3"],
        cover_photo_id="1"
    )
    assert len(group.photos) == 3
    assert group.cover_photo_id == "1"
