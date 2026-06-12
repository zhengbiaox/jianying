from photopicker.backend.models import PhotoInfo, PhotoGrade, SceneGroup, FilterLevel, RejectionReason, GroupState, SessionState

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

def test_rejection_reason_values():
    assert RejectionReason.BLURRY.value == "blurry"
    assert RejectionReason.OVEREXPOSED.value == "overexposed"
    assert RejectionReason.CLOSED_EYES.value == "closed_eyes"

def test_group_state_undo():
    gs = GroupState(id="g1", images=["a.jpg", "b.jpg", "c.jpg"])
    gs.left = "a.jpg"
    gs.right = "b.jpg"
    gs.pending = ["c.jpg"]
    gs.save_snapshot()
    gs.winner = "a.jpg"
    gs.finished = True
    gs.undo()
    assert gs.winner is None
    assert gs.finished is False

def test_session_state_save_load():
    state = SessionState(
        folder="/photos",
        groups=[GroupState(id="g1", images=["a.jpg", "b.jpg"])],
        current_group=0
    )
    data = state.to_dict()
    restored = SessionState.from_dict(data)
    assert restored.folder == "/photos"
    assert len(restored.groups) == 1
