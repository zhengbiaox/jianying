import tempfile
from photopicker.backend.state import save_session, load_session, delete_session
from photopicker.backend.models import SessionState, GroupState

def test_save_and_load_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        state = SessionState(
            folder=tmpdir,
            groups=[GroupState(id="g1", images=["a.jpg", "b.jpg"])],
            current_group=0,
            threshold=0.75,
        )
        save_session(state, tmpdir)
        loaded = load_session(tmpdir)
        assert loaded is not None
        assert loaded.folder == tmpdir
        assert len(loaded.groups) == 1
        assert loaded.threshold == 0.75

def test_load_nonexistent_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        loaded = load_session(tmpdir)
        assert loaded is None

def test_delete_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        state = SessionState(folder=tmpdir)
        save_session(state, tmpdir)
        delete_session(tmpdir)
        assert load_session(tmpdir) is None
