import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from Src.Connections import NetClient
from Src.Host import Host
from Src.User import PlayerIdentity
from Src.bubble import BubbleWindow
from Src.chat import bubble_position
from Src.chat_input import ChatInputWindow
from Src.hotkey import GlobalHotkey
from Src.menu import MenuWindow
from Src.sprite_window import SpriteWindow
from Src.world import World, Sprite

SPRITES_DIR = Path(__file__).resolve().parent.parent / "Sprites"
FLOOR_FRACTION = 0.9          # baseline y for sprites
SEND_INTERVAL = 0.1           # seconds between own-state broadcasts


def should_broadcast(changed: bool, accum: float, interval: float, anim_changed: bool) -> bool:
    """Broadcast own state when something changed AND either the throttle
    interval elapsed or the animation just changed (so idle/walk transitions
    are never dropped by the throttle)."""
    return changed and (accum >= interval or anim_changed)


class AppController:
    def __init__(self, relay_url: str):
        self.app = QApplication.instance() or QApplication(sys.argv)

        self.relay_url = relay_url
        self.identity: PlayerIdentity | None = None
        self.host = Host()
        self.world: World | None = None
        self.windows: dict[str, SpriteWindow] = {}   # sprite id -> window
        self.bubbles: dict[str, BubbleWindow] = {}   # sprite id -> bubble
        self._hotkey_attempted = False
        self._send_accum = 0.0
        self._last_sent_anim: str | None = None

        self.net = NetClient()
        self.menu = MenuWindow()
        self.menu.create_requested.connect(self._on_create)
        self.menu.join_requested.connect(self._on_join)
        self.net.room_created.connect(self._on_room_created)
        self.net.room_joined.connect(self._on_room_joined)
        self.net.member_joined.connect(self._on_member_joined)
        self.net.member_left.connect(self._on_member_left)
        self.net.remote_state.connect(self._on_remote_state)
        self.net.error_occurred.connect(self.menu.show_error)
        self.net.disconnected.connect(self._on_disconnected)
        self.net.chat_received.connect(self._on_chat)

        self.chat_input = ChatInputWindow()
        self.chat_input.submitted.connect(self._on_chat_submit)
        self.hotkey = GlobalHotkey()
        self.hotkey.activated.connect(self._open_composer_for_own)

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)

    # ---- menu actions ----
    def _on_create(self, name, character):
        self.identity = PlayerIdentity(name, character)
        self.net.start_create(self.relay_url, name, character)

    def _on_join(self, code, name, character):
        self.identity = PlayerIdentity(name, character)
        self.net.start_join(self.relay_url, code, name, character)

    # ---- network events ----
    def _on_room_created(self, code, your_id):
        self.host.remember(code, your_id)
        self.menu.show_code(code)
        self._begin_world(your_id)

    def _on_room_joined(self, your_id, members):
        self.host.remember(None, your_id)
        self._begin_world(your_id)
        for mem in members:
            self._add_remote(mem["id"], mem["name"], mem["character"])
        self.menu.hide()

    def _on_member_joined(self, mem):
        if self.world:
            self._add_remote(mem["id"], mem["name"], mem["character"])

    def _on_member_left(self, mid):
        if self.world:
            self.world.remove_member(mid)
        w = self.windows.pop(mid, None)
        if w:
            w.close()
        b = self.bubbles.pop(mid, None)
        if b:
            b.close()

    def _on_remote_state(self, msg):
        if self.world:
            self.world.apply_state(msg["id"], msg["x"], msg["y"],
                                   msg["facing"], msg["anim"])

    def _on_disconnected(self):
        self.timer.stop()
        for w in self.windows.values():
            w.close()
        self.windows.clear()
        for b in self.bubbles.values():
            b.close()
        self.bubbles.clear()
        self.world = None
        self._last_sent_anim = None
        self._send_accum = 0.0
        self.menu.show()
        self.menu.show_error("Disconnected from relay.")

    # ---- world/render setup ----
    def _begin_world(self, your_id):
        if self.world is not None:
            return
        own = Sprite(id=your_id, name=self.identity.name,
                     character=self.identity.character, y=FLOOR_FRACTION,
                     target_y=FLOOR_FRACTION)
        self.world = World(own)
        self.windows[your_id] = SpriteWindow(self.identity.character, SPRITES_DIR)
        self.windows[your_id].clicked.connect(self._open_composer_for_own)
        if not self._hotkey_attempted:
            self._hotkey_attempted = True
            self.hotkey.start()   # False if the OS denied it; click still works
        self.timer.start(16)   # ~60 fps

    def _add_remote(self, mid, name, character):
        self.world.add_member(mid, name, character)
        self.windows[mid] = SpriteWindow(character, SPRITES_DIR)

    # ---- chat ----
    def _open_composer_for_own(self):
        if not self.world:
            return
        win = self.windows.get(self.world.own.id)
        if win is None:
            return
        self.chat_input.open_at(win.x(), win.y() - 36)

    def _on_chat_submit(self, text):
        if not self.world:
            return
        own = self.world.own
        self.net.send_chat(own.id, text)
        self._show_bubble(own.id, text)      # local echo

    def _on_chat(self, msg):
        self._show_bubble(msg["id"], msg["text"])

    def _show_bubble(self, sid, text):
        if sid not in self.windows:
            return
        bub = self.bubbles.get(sid)
        if bub is None:
            bub = BubbleWindow()
            self.bubbles[sid] = bub
        bub.set_text(text)

    # ---- main loop ----
    def _tick(self):
        if not self.world:
            return
        dt = 0.016
        changed = self.world.tick(dt)

        screen = QGuiApplication.primaryScreen().geometry()
        for sp in self.world.all_sprites():
            win = self.windows.get(sp.id)
            if not win:
                continue
            px = int(sp.x * (screen.width() - win.width()))
            py = int(sp.y * (screen.height() - win.height()))
            win.set_position(px, py)
            win.set_facing(sp.facing)
            win.set_animation(sp.anim)
            win.tick(dt)

        for sid, bub in list(self.bubbles.items()):
            bub.tick(dt)
            win = self.windows.get(sid)
            if bub.done or win is None:
                bub.close()
                del self.bubbles[sid]
                continue
            bx, by = bubble_position(win.x(), win.y(), win.width(),
                                     bub.width(), bub.height(), screen.width())
            bub.move(bx, by)

        self._send_accum += dt
        own = self.world.own
        anim_changed = own.anim != self._last_sent_anim
        if should_broadcast(changed, self._send_accum, SEND_INTERVAL, anim_changed):
            self._send_accum = 0.0
            self._last_sent_anim = own.anim
            self.net.send_state(own.id, own.x, own.y, own.facing, own.anim)

    def run(self) -> int:
        self.menu.show()
        return self.app.exec()
