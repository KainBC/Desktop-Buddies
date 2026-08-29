import random
from Src.User import PlayerIdentity
from Src.world import Sprite, OwnController, World, IDLE, WALK


def test_identity_holds_name_and_character():
    ident = PlayerIdentity(name="Kain", character="cat")
    assert (ident.name, ident.character) == ("Kain", "cat")


def test_own_controller_starts_idle_then_walks():
    s = Sprite(id="me", name="Kain", character="cat", x=0.5, y=0.9)
    ctrl = OwnController(s, rng=random.Random(1))
    assert s.anim == IDLE
    ctrl.update(10.0)          # exceed any idle interval
    assert s.anim == WALK
    assert s.target_x != s.x   # picked a destination to walk toward


def test_own_controller_reaches_target_and_returns_to_idle():
    s = Sprite(id="me", name="Kain", character="cat", x=0.5, y=0.9)
    ctrl = OwnController(s, rng=random.Random(1))
    ctrl.update(10.0)                 # -> WALK toward some target
    target = s.target_x
    for _ in range(1000):             # walk until arrival
        ctrl.update(0.1)
        if s.anim == IDLE:
            break
    assert s.anim == IDLE
    assert abs(s.x - target) < 0.01


def test_own_controller_faces_direction_of_travel():
    s = Sprite(id="me", name="Kain", character="cat", x=0.5, y=0.9)
    ctrl = OwnController(s, rng=random.Random(1))
    ctrl.update(10.0)                       # -> WALK, target chosen from x=0.5
    expected = 1 if s.target_x >= 0.5 else -1
    ctrl.update(0.1)                        # take a step toward the target
    assert s.facing == expected


def test_world_add_apply_and_lerp_remote():
    own = Sprite(id="me", name="Kain", character="cat")
    world = World(own)
    world.add_member("them", "Sam", "dog")
    world.apply_state("them", x=1.0, y=0.9, facing=-1, anim=WALK)

    before = world.remotes["them"].x
    for _ in range(200):
        world.tick(0.05)
    after = world.remotes["them"].x
    assert after > before               # moved toward target 1.0
    assert abs(after - 1.0) < 0.01
    assert world.remotes["them"].facing == -1


def test_world_remove_member():
    world = World(Sprite(id="me", name="Kain", character="cat"))
    world.add_member("them", "Sam", "dog")
    world.remove_member("them")
    assert "them" not in world.remotes
    assert [sp.id for sp in world.all_sprites()] == ["me"]


# --- pokes ---

def _world_with_remote():
    world = World(Sprite(id="me", name="Kain", character="cat"))
    world.add_member("them", "Sam", "dog")
    return world


def test_poke_starts_a_hop_on_a_remote_sprite():
    world = _world_with_remote()
    assert world.hop_offset("them") == 0.0
    world.poke("them")
    world.tick(0.2)                       # partway up the arc
    assert world.hop_offset("them") > 0.0


def test_poke_starts_a_hop_on_the_owned_sprite():
    """The poked player's own client hops the sprite it owns."""
    world = _world_with_remote()
    world.poke("me")
    world.tick(0.2)
    assert world.hop_offset("me") > 0.0


def test_poke_ignores_unknown_ids():
    world = _world_with_remote()
    world.poke("ghost")
    world.tick(0.2)
    assert world.hop_offset("ghost") == 0.0


def test_hop_expires_and_is_dropped():
    world = _world_with_remote()
    world.poke("them")
    for _ in range(20):
        world.tick(0.05)                  # 1.0s, well past the hop duration
    assert world.hop_offset("them") == 0.0
    assert "them" not in world.hops


def test_second_poke_restarts_rather_than_stacking():
    world = _world_with_remote()
    world.poke("them")
    world.tick(0.4)                       # near the end of the arc
    world.poke("them")                    # restart
    assert len(world.hops) == 1
    world.tick(0.2)                       # would be finished without the reset
    assert world.hop_offset("them") > 0.0


def test_hop_does_not_disturb_sprite_coordinates():
    """The hop is a render offset, not a position change."""
    world = _world_with_remote()
    before = world.remotes["them"].y
    world.poke("them")
    world.tick(0.2)
    assert world.remotes["them"].y == before


def test_removing_a_member_drops_their_hop():
    world = _world_with_remote()
    world.poke("them")
    world.remove_member("them")
    assert "them" not in world.hops
