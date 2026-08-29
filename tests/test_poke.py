from Src.poke import Hop


def test_hop_starts_on_the_ground():
    hop = Hop(height=0.04, duration=0.45)
    assert hop.offset() == 0.0
    assert not hop.done


def test_hop_peaks_at_height_midway():
    hop = Hop(height=0.04, duration=0.45)
    hop.advance(0.225)
    assert abs(hop.offset() - 0.04) < 1e-6


def test_hop_returns_to_ground_at_end():
    hop = Hop(height=0.04, duration=0.45)
    hop.advance(0.45)
    assert abs(hop.offset()) < 1e-6
    assert hop.done


def test_hop_arc_is_symmetric():
    """A quarter of the way up matches a quarter of the way down."""
    rising = Hop(height=0.04, duration=0.4)
    rising.advance(0.1)
    falling = Hop(height=0.04, duration=0.4)
    falling.advance(0.3)
    assert abs(rising.offset() - falling.offset()) < 1e-6
    assert rising.offset() > 0.0            # and it actually left the ground


def test_hop_never_sinks_below_the_ground():
    hop = Hop(height=0.04, duration=0.45)
    hop.advance(10.0)                       # long past the end
    assert hop.offset() == 0.0


def test_hop_offset_does_not_mutate_configuration():
    """offset() reads state; it must not write to height or duration."""
    hop = Hop(height=0.04, duration=0.45)
    hop.advance(0.225)
    first = hop.offset()
    second = hop.offset()
    assert first == second
    assert hop.height == 0.04
    assert hop.duration == 0.45


def test_hop_advance_accumulates():
    hop = Hop(height=0.04, duration=0.4)
    hop.advance(0.1)
    hop.advance(0.1)
    assert abs(hop.offset() - 0.04) < 1e-6   # two steps reached the midpoint


def test_hop_reset_restarts_the_arc():
    hop = Hop(height=0.04, duration=0.45)
    hop.advance(1.0)
    assert hop.done
    hop.reset()
    assert not hop.done
    assert hop.offset() == 0.0


def test_default_height_is_a_small_screen_fraction():
    """Offsets are fractions of screen height, like Sprite.x/y."""
    hop = Hop()
    assert 0.0 < hop.height <= 0.1
