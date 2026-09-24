from dataclasses import dataclass, field


@dataclass
class Incoming:
    wa_message_id: str
    wa_id: str
    type: str  # text | interactive | image | other
    text: str | None = None
    option_id: str | None = None
    media_id: str | None = None
    mime_type: str | None = None
    profile_name: str | None = None


@dataclass
class Out:
    body: str
    options: list[tuple[str, str]] = field(default_factory=list)  # (id, título)
