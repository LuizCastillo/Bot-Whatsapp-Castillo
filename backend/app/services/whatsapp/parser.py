from app.schemas.messaging import Incoming


def parse_webhook(payload: dict, expected_phone_id: str) -> list[Incoming]:
    """Extrai mensagens recebidas. Ignora status de entrega e números de outra conta."""
    result: list[Incoming] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            if (value.get("metadata") or {}).get("phone_number_id") != expected_phone_id:
                continue
            names = {c.get("wa_id"): (c.get("profile") or {}).get("name") for c in value.get("contacts") or []}
            for m in value.get("messages") or []:
                wa_id, mid, mtype = m.get("from"), m.get("id"), m.get("type")
                if not wa_id or not mid:
                    continue
                base = dict(wa_message_id=mid, wa_id=str(wa_id), profile_name=names.get(wa_id))
                if mtype == "text":
                    result.append(Incoming(type="text", text=(m.get("text") or {}).get("body"), **base))
                elif mtype == "interactive":
                    inter = m.get("interactive") or {}
                    reply = inter.get("button_reply") or inter.get("list_reply") or {}
                    result.append(Incoming(type="interactive", option_id=reply.get("id"),
                                           text=reply.get("title"), **base))
                elif mtype == "image":
                    img = m.get("image") or {}
                    result.append(Incoming(type="image", media_id=img.get("id"), mime_type=img.get("mime_type"),
                                           text=img.get("caption"), **base))
                else:
                    result.append(Incoming(type="other", **base))
    return result
