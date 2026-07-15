from Src.sprite_window import FrameCycler


def test_cycler_advances_at_fps():
    c = FrameCycler(frame_count=4, fps=10.0)   # 0.1s per frame
    assert c.advance(0.0) == 0
    assert c.advance(0.1) == 1
    assert c.advance(0.25) == 3   # 0.35s total -> frame 3


def test_cycler_wraps_around():
    c = FrameCycler(frame_count=2, fps=10.0)
    c.advance(0.1)                 # -> 1
    assert c.advance(0.1) == 0     # wraps back to 0


def test_cycler_single_frame_stays_at_zero():
    c = FrameCycler(frame_count=1, fps=10.0)
    assert c.advance(5.0) == 0


def test_cycler_reset():
    c = FrameCycler(frame_count=4, fps=10.0)
    c.advance(0.3)
    c.reset()
    assert c.advance(0.0) == 0
