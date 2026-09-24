import re


def normalize_br_phone(raw: str) -> str:
    """Devolve dígitos em formato canônico (55 + DDD + número com 9º dígito).

    O wa_id de números brasileiros antigos pode vir sem o 9º dígito.
    Use o valor canônico para cadastro/busca (UNIQUE) e o wa_id original
    para responder pela Cloud API.
    """
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        raise ValueError("Telefone vazio.")
    if digits.startswith("55") and len(digits) == 12 and digits[4] in "6789":
        digits = digits[:4] + "9" + digits[4:]
    return digits
