from dataclasses import dataclass


@dataclass
class Host:
    """Tracks the room this client created/joined and its assigned id."""
    code: str | None = None
    your_id: str | None = None

    def remember(self, code: str | None, your_id: str) -> None:
        self.code = code
        self.your_id = your_id
