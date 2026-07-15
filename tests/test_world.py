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
