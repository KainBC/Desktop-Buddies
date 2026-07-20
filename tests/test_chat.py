from Src.chat import sanitize_chat, BubbleLifetime, bubble_position


def test_sanitize_trims_and_collapses_whitespace():
    assert sanitize_chat("  hello    world  ") == "hello world"
    assert sanitize_chat("line1\n\nline2") == "line1 line2"


def test_sanitize_empty_returns_empty():
    assert sanitize_chat("") == ""
    assert sanitize_chat("    \n\t ") == ""


def test_sanitize_caps_length():
    assert sanitize_chat("a" * 200, max_len=140) == "a" * 140


def test_lifetime_full_opacity_during_hold():
    life = BubbleLifetime(hold=5.0, fade=0.5)
    assert life.opacity() == 1.0
    assert not life.done
    life.advance(5.0)
    assert life.opacity() == 1.0
    assert not life.done


def test_lifetime_fades_then_done():
    life = BubbleLifetime(hold=5.0, fade=0.5)
    life.advance(5.25)                       # halfway through the fade
    assert abs(life.opacity() - 0.5) < 1e-6
    life.advance(0.25)                       # end of fade
    assert life.opacity() == 0.0
    assert life.done


def test_lifetime_reset():
    life = BubbleLifetime(hold=0.1, fade=0.1)
    life.advance(1.0)
    assert life.done
    life.reset()
    assert not life.done
    assert life.opacity() == 1.0


def test_bubble_position_centers_and_sits_above():
    x, y = bubble_position(sprite_x=100, sprite_y=300, sprite_w=64,
                           bubble_w=120, bubble_h=40, screen_w=1000, gap=8)
    assert x == 100 + (64 - 120) // 2        # centered (may be left of sprite_x)
    assert y == 300 - 40 - 8


def test_bubble_position_clamps_to_screen():
    # far left sprite -> bubble clamped to x=0
    x, _ = bubble_position(0, 300, 20, 120, 40, 1000)
    assert x == 0
    # far right sprite -> bubble clamped to screen_w - bubble_w
    x, _ = bubble_position(980, 300, 20, 120, 40, 1000)
    assert x == 1000 - 120
    # near top -> bubble clamped to y=0
    _, y = bubble_position(100, 10, 64, 120, 40, 1000)
    assert y == 0
