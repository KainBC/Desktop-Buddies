# Desktop Buddies — Buddy Encounters

## Summary

When two buddies wander into each other on screen, they sometimes stop and
have a conversation: both play a looping `talk` animation, facing each other,
for a random 45–120 seconds, then go back to wandering.

The feature is deliberately small in protocol terms. `anim` already travels
in every state packet, so the *rendering* of an encounter is nearly free —
the real work is getting two independently-authoritative clients to agree
that an encounter happened, when it started, and how long it lasts.

This spec covers the coordination rule, the new pure `Src/encounter.py`
module, the `talk` art, and the handful of existing behaviours that have to
change to accommodate a buddy that is deliberately standing still.

## Goals

- Two buddies that wander into each other sometimes stop and talk.
- Both people see the same encounter, start and end at the same moment, for
  the same duration — no client-by-client disagreement.
- No change to the relay, and therefore no relay redeploy.
- A client running an older build degrades quietly rather than breaking.
- The encounter logic is pure and headless-testable, matching the
  client-side convention that logic is separate from Qt rendering.
- Chat keeps working during an encounter; the talk animation and chat
  bubbles are independent and coexist.

## Non-Goals

- **No new message type.** See "Design Decisions".
- **No relay involvement.** The relay stays dumb and sprite-ignorant.
- **No group conversations.** Encounters are strictly pairwise; a third
  buddy is not pulled in.
- **No conversation content.** Nothing is said; this is ambient animation,
  not chat. Real chat remains the existing bubble system.
- **No pathfinding.** Buddies do not seek each other out. An encounter is
  incidental — a consequence of ordinary wandering.
- **No vertical movement.** Buddies remain pinned to their floor line.
- **No new customization slot.** `talk` is an animation, not a slot.

## Design Decisions

Five choices shape everything else.

**The initiator owns the duration; the responder mirrors.** Both clients
detect the overlap independently, but only one decides. The owner of the
lower id — a deterministic tiebreak both sides compute identically — rolls
the probability, picks a duration, and enters `talk`. The other client sees
a remote sprite overlapping it, in `talk`, naming it as partner, and mirrors:
it freezes and plays `talk` too. When the initiator's timer expires it
returns to `idle`; the responder sees that and ends as well.

Two clients cannot disagree about a number only one of them owns. The
alternative — broadcasting an agreed duration to both — is symmetric and
more obvious, but requires a new message type, which requires a relay
change, which requires a redeploy before the feature works at all.

**The encounter rides on the existing `STATE` message.** `anim` is already
on the wire. The single new piece of information is *who* a talking buddy is
talking to, which becomes an optional `partner` field in the `STATE`
payload. The relay forwards `STATE` raw, so it needs no change. The field is
backward compatible in both directions: an older client reads only the five
keys it knows and ignores `partner`; a newer client reads `msg.get("partner")`
and defaults to `None`.

**`partner` exists to disambiguate crowds.** With two buddies, `anim ==
"talk"` alone would be enough. With three or more, a buddy could overlap
someone who is already talking to a third party and wrongly mirror them.
Naming the partner makes the pairing explicit, so a responder mirrors only
an initiator that actually named *it*.

**Encounters are strictly pairwise.** A buddy already in an encounter is
never proposed to, and a third buddy wandering into a pair is ignored. Group
behaviour would need a real conversation model — who joins, who leaves, what
the animation means with four participants — and buys nothing for a feature
whose point is two characters bumping into each other.

**The probability roll lives on the initiator only.** Exactly one side rolls,
so "sometimes" cannot mean "sometimes for you and always for them."

## The Coordination Rule

Written out precisely, because this is the part that is easy to get subtly
wrong.

**Every tick, on every client:**

1. If our own buddy is in an encounter, advance it. If it is over, return to
   `idle` and start the pair's cooldown. Done.

2. Otherwise, if our own buddy is *not* in an encounter, look at each remote
   sprite `r`:

   **Responder path** — mirror an initiator that named us:
   - `r.anim == "talk"` and `r.partner == own.id`, and
   - `initiator(own.id, r.id) == r.id` (they really are the initiator for
     this pair).

     Then enter an encounter with `r` as partner, and set our own
     `partner = r.id`.

   **Initiator path** — propose, if we are the one who decides:
   - `initiator(own.id, r.id) == own.id`, and
   - `overlaps(own.x, r.x)`, and
   - `r.anim != "talk"` (they are not already busy), and
   - the pair `(own.id, r.id)` is not on cooldown.

     Then roll `CHANCE`. On a win, pick `duration` uniformly in
     `[MIN_SECONDS, MAX_SECONDS]`, enter an encounter, and set
     `partner = r.id`. On a loss, put the pair on cooldown so the roll is
     not repeated every frame.

3. While in an encounter, the buddy does not wander: `OwnController.update`
   is skipped. `facing` is set toward the partner once, on entry.

**`initiator(a, b)`** returns `min(a, b, key=lambda s: (len(s), s))`.
Determinism is the only real requirement — both sides must compute the same
answer from the same two ids. Sorting by `(length, value)` additionally
orders the relay's decimal-string ids numerically, so `"2"` precedes `"10"`
rather than following it as a plain string compare would.

**`overlaps(ax, bx)`** is `abs(ax - bx) < OVERLAP_X`. Positions are
fractional, and the renderer maps them as `px = x * (screen_width -
sprite_width)`, so two sprites visually touch when
`abs(ax - bx) * (W - w) < w`. For a 64px sprite on a 1920px screen that is
about `0.034`. `OVERLAP_X = 0.04` is a slightly generous constant, kept in
the pure module rather than derived from screen geometry so `encounter.py`
stays free of Qt and remains unit-testable.

## Architecture

New module **`Src/encounter.py`** — pure Python, no Qt, no network, no
filesystem. It occupies the same role as `Src/poke.py`: the headless core of
one interaction.

```
Src/encounter.py
  OVERLAP_X    = 0.04    fraction of screen width
  CHANCE       = 0.25    probability an overlap becomes an encounter
  MIN_SECONDS  = 45.0
  MAX_SECONDS  = 120.0
  PAIR_COOLDOWN = 180.0  before the same pair may trigger again
  MIRROR_SLACK = 15.0    responder's safety cap beyond MAX_SECONDS

  overlaps(ax, bx) -> bool
  initiator(a, b)  -> str
  pair_key(a, b)   -> tuple[str, str]      order-independent cooldown key

  class Encounter        one live encounter
      partner: str
      duration: float
      elapsed: float
      advance(dt) -> None
      done -> bool

  class Director         the decision layer
      __init__(rng=None)
      active: Encounter | None
      consider(own_id, own_x, remotes) -> Encounter | None
      advance(dt) -> bool
      end() -> bool
      drop_partner(id) -> bool
```

**`Director` decides; `World` applies.** The split matters: `Director` owns
timing, rolling and cooldowns and touches no `Sprite`; `World` translates its
answers into `anim`, `facing` and `partner` on the sprite. That is what keeps
`encounter.py` free of the world model and independently testable.

- `consider(own_id, own_x, remotes)` is called only when no encounter is
  active. `remotes` is any iterable of objects exposing `.id`, `.x`, `.anim`
  and `.partner` — `Sprite` satisfies this by duck typing, so
  `encounter.py` never imports `world.py`. It runs the responder check
  first, then the initiator check, and returns the `Encounter` it started or
  `None`. It is also what records a lost roll's cooldown.
- `advance(dt)` advances an active encounter and returns `True` on the tick
  it ends (having cleared `active` and started the pair's cooldown). It also
  expires stale cooldown entries.
- `end()` ends an active encounter immediately, returning `True` if there was
  one. This is the single path for early termination — a future "move your
  buddy" control calls it.
- `drop_partner(id)` ends an active encounter if `id` is its partner,
  returning `True` if it did. `World.remove_member` calls it.

`Director` takes an injectable rng defaulting to `random.Random()`, exactly
as `OwnController` does, so tests are deterministic rather than flaky.

### Changes to existing modules

| File | Change |
|------|--------|
| `Src/encounter.py` | **New.** Constants, `overlaps`, `initiator`, `pair_key`, `Encounter`, `Director`. |
| `Src/world.py` | `Sprite` gains `partner: str \| None = None`. `World` owns a `Director`, gates `OwnController.update` on it, and reports encounter transitions from `tick`. `apply_state` accepts and stores `partner`. |
| `Src/Connections.py` | `send_state` gains an optional `partner` argument, encoded into the `STATE` payload. |
| `Src/app.py` | `_on_remote_state` passes `msg.get("partner")` through. The broadcast call passes `own.partner`. |
| `Src/sprite_window.py` | The hardcoded `{"idle", "walk"}` frame dict becomes a module-level `ANIMS = ("idle", "walk", "talk")`, built in a loop. |
| `tools/make_placeholder_sprites.py` | Generates `Bodies/<body>/talk/` frames, and a matching `Faces/default/talk/` frame. |
| `Sprites/Bodies/*/talk/` | **New art**, generated. White, tintable, same 64×64 canvas as every other body frame. |

Nothing in `relay/` or `shared/` changes.

### The `talk` art

Bodies are authored white and tinted at load, so `talk` frames follow the
same rule as `idle` and `walk` — no special handling, no new slot, no
manifest change. The generator emits a short loop (2 frames) per body: a
small lean-and-settle, distinct from `idle`'s breathing bob so the two read
differently at a glance.

`Faces/default/` gets a `talk/` frame as well, because `composite_frames`
truncates a layer against the base layer's frame count and a body with no
matching face art for an animation would composite oddly. One frame is
enough — the compositor repeats a short layer via `frames[i % len(frames)]`.

`SpriteWindow` currently builds its frame dict from two hardcoded keys. That
becomes a loop over `ANIMS`, so a future animation is one tuple entry rather
than another pair of lines.

## Error Handling & Edge Cases

- **`should_broadcast` would swallow the transition.** It is
  `changed and (accum >= interval or anim_changed)`, and `changed` comes from
  `OwnController.update`, which a frozen buddy never calls. Entering `talk`
  would therefore never be broadcast and no peer would ever see it.
  `World.tick` must return `True` on encounter start and end. This is the
  single most important detail in the spec; the feature silently does
  nothing without it.

- **A stalled peer must not freeze you forever.** If the initiator's packets
  stop arriving without a clean disconnect, the responder would mirror
  indefinitely. The responder caps its own encounter at
  `MAX_SECONDS + MIRROR_SLACK` and resumes regardless.

- **Partner disconnects.** `MEMBER_LEFT` removes the sprite; `World` ends any
  encounter whose partner is no longer present, on the same tick.

- **Partner stops talking early.** The responder ends when the partner's
  `anim` is no longer `talk`, or no longer names it as partner.

- **Simultaneous proposals.** Two initiators could both propose to the same
  buddy within one network round trip. The responder mirrors whichever it
  sees first and ignores the other; the losing initiator talks to nobody
  until its timer expires. The window is milliseconds against an overlap
  lasting seconds, and the state is self-healing, so this is accepted rather
  than solved with an acknowledgement round trip.

- **Older clients.** `set_animation` already guards with `name in
  self._frames`, so a client without `talk` art ignores the animation instead
  of crashing. It will show the buddy standing still in its previous
  animation — a cosmetic oddity in mixed-version rooms, not a break.

- **Solo play.** With no remotes there are no pairs, so nothing triggers.

- **Chat during an encounter.** Explicitly supported. The talk animation and
  the chat bubble are independent; sending a message does not end the
  encounter.

- **Cooldown growth.** `cooldowns` is keyed by pair and entries are dropped
  once expired, so the dict cannot grow without bound across a long session.

## Testing

**Unit tests (`tests/test_encounter.py`), pure and headless:**

- `overlaps` — true just inside the threshold, false just outside, symmetric.
- `initiator` — stable regardless of argument order; `"2"` precedes `"10"`.
- `pair_key` — identical for `(a, b)` and `(b, a)`.
- `Encounter` — `done` only after `duration`; `advance` accumulates.
- `Director` — duration lands within `[MIN_SECONDS, MAX_SECONDS]` under a
  seeded rng; a lost roll sets a cooldown; a pair on cooldown is not
  re-rolled; a busy partner is never proposed to; expiry clears the active
  encounter and starts the cooldown; expired cooldown entries are dropped.

**World-level tests (`tests/test_world.py`):**

- A buddy in an encounter does not wander — `x` is unchanged across ticks.
- `tick` returns `True` on the tick an encounter starts and on the tick it
  ends, so the transition is broadcast.
- An encounter ends when its partner is removed.
- The responder path mirrors only an initiator that names it, and only when
  the tiebreak agrees.
- The responder's safety cap fires at `MAX_SECONDS + MIRROR_SLACK`.

Written test-first, as the rest of the client is.

## Open Considerations (not blocking)

- **Constants are guesses.** 25%, 45–120s and a 3-minute cooldown are
  starting points chosen to be visible during testing without being
  constant. They live together at the top of one module precisely so they
  can be tuned from observation.
- **Ending an encounter early** has exactly one code path, so a future
  "move your buddy" control can call it. No such control exists today.
- **Richer encounters** — reactions, a wave on parting, more than two
  participants — are deliberately out of scope and would each need their own
  design.
