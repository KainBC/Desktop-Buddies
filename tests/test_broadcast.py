from Src.app import should_broadcast


def test_should_broadcast_false_when_nothing_changed():
    assert should_broadcast(changed=False, accum=1.0, interval=0.1, anim_changed=True) is False


def test_should_broadcast_true_when_interval_elapsed():
    assert should_broadcast(changed=True, accum=0.1, interval=0.1, anim_changed=False) is True


def test_should_broadcast_true_when_anim_changed_even_if_throttled():
    # the bug case: interval hasn't elapsed yet, but the animation just
    # transitioned (e.g. walk -> idle on arrival) so it must still flush.
    assert should_broadcast(changed=True, accum=0.01, interval=0.1, anim_changed=True) is True


def test_should_broadcast_false_when_throttled_and_anim_unchanged():
    assert should_broadcast(changed=True, accum=0.01, interval=0.1, anim_changed=False) is False
