from app.schemas.messaging import Out

MAX_BUTTONS = 3
MAX_LIST_ROWS = 10


def build_payload(to: str, out: Out) -> dict:
    base = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": to}
    opts = out.options
    if not opts:
        return {**base, "type": "text", "text": {"body": out.body[:4096], "preview_url": False}}
    if len(opts) <= MAX_BUTTONS:
        buttons = [{"type": "reply", "reply": {"id": oid[:256], "title": title[:20]}} for oid, title in opts]
        return {**base, "type": "interactive", "interactive": {
            "type": "button", "body": {"text": out.body[:1024]}, "action": {"buttons": buttons}}}
    if len(opts) <= MAX_LIST_ROWS:
        rows = []
        for oid, title in opts:
            row = {"id": oid[:200], "title": title[:24]}
            if len(title) > 24:
                row["description"] = title[:72]
            rows.append(row)
        return {**base, "type": "interactive", "interactive": {
            "type": "list", "body": {"text": out.body[:1024]},
            "action": {"button": "Ver opções", "sections": [{"title": "Opções", "rows": rows}]}}}
    numbered = "\n".join(f"{i}. {title}" for i, (_, title) in enumerate(opts, 1))
    return {**base, "type": "text", "text": {"body": f"{out.body}\n\n{numbered}"[:4096], "preview_url": False}}


def message_type(out: Out) -> str:
    if not out.options:
        return "TEXT"
    return "BUTTON" if len(out.options) <= MAX_BUTTONS else "LIST"
