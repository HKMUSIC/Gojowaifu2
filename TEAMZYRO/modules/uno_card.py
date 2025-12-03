# TEAMZYRO/modules/uno_card.py
# Helper to map UNO card codes -> Telegram sticker file_id
from typing import Dict, Optional, Tuple, List

# -------------------------
# STICKER_MAP (provided by you)
# -------------------------
STICKER_MAP: Dict[str, str] = {

    # ===== BLUE =====
    "BLUE_0": "AAMCBAADGQEAARlLKmkwDP5SUibcrdkOH_xiiJj-NWguAALZAQACX1eZAAEqnpNt3SpG_wEAB20AAzYE",
    "BLUE_1": "AAMCBAADGQEAARlLLGkwDUFfKwQX3CHoqi2IuX390_8zAALbAQACX1eZAAHluPl_BVzaDgEAB20AAzYE",
    "BLUE_2": "AAMCBAADGQEAARlLLmkwDVOUHGOaJlk_xBqDzpo7AAE4dAAC3QEAAl9XmQABBXuSQXaT_nMBAAdtAAM2BA",
    "BLUE_3": "AAMCBAADGQEAARlLMGkwDWFRF_SrgW6E9Ip9p7x3NymmAALhAQACX1eZAAHo1SP4devY_wEAB20AAzYE",
    "BLUE_4": "AAMCBAADGQEAARlLNGkwDXr859qCw9bvo-bKgrnBVwvUAALjAQACX1eZAALf6g-FruzaAQAHbQADNgQ",
    "BLUE_5": "AAMCBAADGQEAARlLNmkwDZmwj1nOBSc6iYkcUk1_dYNAAALlAQACX1eZAAHwMoU1Nb4OggEAB20AAzYE",
    "BLUE_6": "AAMCBAADGQEAARlLOGkwDaef5r8qQiOuh0CnQEZflQQ2AALpAQACX1eZAAHmKrizqjwJ3gEAB20AAzYE",
    "BLUE_7": "AAMCBAADGQEAARlLPGkwDbreP469leoN7-LIQDXq74vZAALrAQACX1eZAAHvul-ZztVWigEAB20AAzYE",
    "BLUE_8": "AAMCBAADGQEAARlLPmkwDcltjxWvEF6T3i-nnCs4AsZsAALtAQACX1eZAAGdURg9n6qvEwEAB20AAzYE",
    "BLUE_9": "AAMCBAADGQEAARlLQGkwDdnvci14d6zmWjTdeMupm4geAALvAQACX1eZAAFjAZc535XzNQEAB20AAzYE",
    "BLUE_SKIP": "AAMCBAADGQEAARlLGmkwDIs0VGlJ9SkY76PK3-7ID_EYAAL1AQACX1eZAAHXOgABZUCgVkkBAAdtAAM2BA",
    "BLUE_REVERSE": "AAMCBAADGQEAARlLRGkwDfbpgkzgGAihZLJnI9kISQ4oAALzAQACX1eZAAHI5jbpFQE9bAEAB20AAzYE",
    "BLUE_DRAW_TWO": "AAMCBAADGQEAARlLQmkwDeXCVoQVlZbwDTXLSBJC_VacAALxAQACX1eZAAHAf0ks_Y82JwEAB20AAzYE",

    # ===== RED =====
    "RED_0": "AAMCBAADGQEAARlLamkwDwsPkGcqras_rcbt1n187pqYAAIRAgACX1eZAAHK9atgT_cu_gEAB20AAzYE",
    "RED_1": "CAACAgQAAxkBAAEZS2xpMA8ar8LCAAFgn62ZjEU6YTCRpCEAAhMCAAJfV5kAAf_qm3ZqKsURNgQ",
    "RED_2": "AAMCBAADGQEAARlLbmkwDyhq2fGv2SN40ijZq-oJaNw2AAIVAgACX1eZAAHQrmSSeMDfgAEAB20AAzYE",
    "RED_3": "AAMCBAADGQEAARlLcGkwDzdKyW1qHvdr8MrOLnrUKZ19AAIXAgACX1eZAAFeHWWPa-piRwEAB20AAzYE",
    "RED_4": "AAMCBAADGQEAARlLcmkwD0n1ZjAZbY1XHDVo2vINYcQSAAIZAgACX1eZAAE7VUWywkd3KAEAB20AAzYE",
    "RED_5": "AAMCBAADGQEAARlLdGkwD1gFJ0Cy6RRv4tbbfdOzjKt7AAIbAgACX1eZAAF1s0b9V-PUJAEAB20AAzYE",
    "RED_6": "AAMCBAADGQEAARlLdmkwEBTnqcWeobZxpCBQkAut0smTAAIdAgACX1eZAAF8hSz11exIUgEAB20AAzYE",
    "RED_7": "AAMCBAADGQEAARlLeGkwECqIiPRIv0FUK1oUiO-QyNKUAAIfAgACX1eZAAEVnCo1RKSqnAEAB20AAzYE",
    "RED_8": "AAMCBAADGQEAARlLemkwEGQDS5GuFjQDyvClobw3igPkAAIhAgACX1eZAAEhXezQrbzKOgEAB20AAzYE",
    "RED_9": "AAMCBAADGQEAARlLfGkwEHNszaRQPMoq2Jb2K-9BhJjLAAIjAgACX1eZAAHN4GBkUaxpqgEAB20AAzYE",
    "RED_SKIP": "AAMCBAADGQEAARlLgmkwEKCX-Pq3Y5BjZcmEU5VaoqEaAAIpAgACX1eZAAFprUDwYHBu3QEAB20AAzYE",
    "RED_REVERSE": "AAMCBAADGQEAARlLgGkwEJGDlBnDySOiv3OGG-nUFhurAAInAgACX1eZAAGay7EvXnoVZgEAB20AAzYE",
    "RED_DRAW_TWO": "AAMCBAADGQEAARlLfmkwEINRih7eNjPJmyLna5i6R6SUAAIlAgACX1eZAAGZvG1zNp2cVgEAB20AAzYE",

    # ===== GREEN =====
    "GREEN_0": "AAMCBAADGQEAARlLSGkwDiAKxlVBVXC9fXqlT5Cs_qs1AAL3AQACX1eZAAH7m-CsNWDzBQEAB20AAzYE",
    "GREEN_1": "AAMCBAADGQEAARlLTGkwDi42pKK45uOsIgw8bKIKab_FAAL5AQACX1eZAAFVNSG--aqs9AEAB20AAzYE",
    "GREEN_2": "AAMCBAADGQEAARlLVGkwDkANvFe0zHLxTismboBuaLcFAAL7AQACX1eZAAHDX5Qn7VbSdAEAB20AAzYE",
    "GREEN_3": "AAMCBAADGQEAARlLVmkwDlBUbDoGY7PoWYEVMyMsr5hJAAL9AQACX1eZAAGwUxSSKSNPagEAB20AAzYE",
    "GREEN_4": "AAMCBAADGQEAARlLWGkwDmA8pSkeyfShiCnMpR-DTk7rAAL_AQACX1eZAAEBEgKqT0vs4AEAB20AAzYE",
    "GREEN_5": "AAMCBAADGQEAARlLWmkwDnV9yh9ZlchQdMojwVd-Q2tKAAIBAgACX1eZAAGN2wN5nVhf3wEAB20AAzYE",
    "GREEN_6": "AAMCBAADGQEAARlLXGkwDoic5PRkznQM44ZB_gYSTT-YAAIDAgACX1eZAAFaJA80kw1XfQEAB20AAzYE",
    "GREEN_7": "AAMCBAADGQEAARlLXmkwDpnk1QTobsOVeksZh-HBjTaaAAIFAgACX1eZAAGDbLTCiNGLBgEAB20AAzYE",
    "GREEN_8": "AAMCBAADGQEAARlLYGkwDqtT8sA403EBa-HerqtLefAMAAIHAgACX1eZAAGnWrRTRZj7gQEAB20AAzYE",
    "GREEN_9": "AAMCBAADGQEAARlLYmkwDr26BeUzPrusFfTR8I4yGFrfAAIJAgACX1eZAAHODOPdhwzltwEAB20AAzYE",
    "GREEN_SKIP": "AAMCBAADGQEAARlLaGkwDu26Ngd9SqLJ8Byq14UvvVHXAAIPAgACX1eZAAHn-hBXxRvYQgEAB20AAzYE",
    "GREEN_REVERSE": "AAMCBAADGQEAARlLZmkwDtzsq22Hbg90-rc9QNhN8Ca3AAINAgACX1eZAAFMYqmCS3vfyQEAB20AAzYE",
    "GREEN_DRAW_TWO": "AAMCBAADGQEAARlLZGkwDs3d9V2X7bezlY7AA9jhiAGoAAILAgACX1eZAAFWg06uGplHVwEAB20AAzYE",

    # ===== YELLOW =====
    "YELLOW_0": "AAMCBAADGQEAARlLhGkwELk6O4G_6MK_kmhB-x8EWkUmAAIrAgACX1eZAAG1mgAB2D5sIc8BAAdtAAM2BA",
    "YELLOW_1": "AAMCBAADGQEAARlLhmkwENm1S3GNQG2ACDnttLXVJFNxAAItAgACX1eZAAHqNCCjuSEQjgEAB20AAzYE",
    "YELLOW_2": "AAMCBAADGQEAARlLiGkwEOc08HUMle1rAAEnKdW5AW8ksAACLwIAAl9XmQAB-LueO6wQIgQBAAdtAAM2BA",
    "YELLOW_3": "AAMCBAADGQEAARlLjGkwEP3P-EBjnhsevcpeC5ILZvEPAAIxAgACX1eZAAFBQ00TMrpMegEAB20AAzYE",
    "YELLOW_4": "AAMCBAADGQEAARlLjmkwEQylQE0-nqZ_tTuQKSl_RNHCAAIzAgACX1eZAAF7IOqIuGqyDQEAB20AAzYE",
    "YELLOW_5": "AAMCBAADGQEAARlLkGkwERzhgjtiPkPU1e7fVLzcWXuRAAI1AgACX1eZAAHyIiYzI-E-LgEAB20AAzYE",
    "YELLOW_6": "AAMCBAADGQEAARlLlGkwES91IHUBFjVqBERKAAFsP7TccgACNwIAAl9XmQAB_xPH7md--IcBAAdtAAM2BA",
    "YELLOW_7": "AAMCBAADGQEAARlLlmkwET3vxsyVqp2Bnw5isSLxYRLRAAI5AgACX1eZAAHPK6qSI6Ku_AEAB20AAzYE",
    "YELLOW_8": "AAMCBAADGQEAARlLmGkwEUuQF8VwULEqvpMPEEi_X4iPAAI7AgACX1eZAAHXiL4XwJi0ewEAB20AAzYE",
    "YELLOW_9": "AAMCBAADGQEAARlLmmkwEV1ChzPNwjtaGkXKUKMabCsNAAI9AgACX1eZAAGG_opl6vQSOAEAB20AAzYE",
    "YELLOW_SKIP": "AAMCBAADGQEAARlLoGkwEbWq3s7foLZ0hZBOvNfO9GCBAAJDAgACX1eZAAF1m63alvMoxwEAB20AAzYE",
    "YELLOW_REVERSE": "AAMCBAADGQEAARlLnmkwEZ9KlIznwCgvTRTFb6NQaMJ4AAJBAgACX1eZAAEIekObsw9tqQEAB20AAzYE",
    "YELLOW_DRAW_TWO": "AAMCBAADGQEAARlLnGkwEWotQ11eIMRsL7ZTExMZ_phYAAI_AgACX1eZAAFrjyuhcA2kswEAB20AAzYE",

    # ===== SPECIAL =====
    "WILD": "AAMCBAADGQEAARlLRGkwDfbpgkzgGAihZLJnI9kISQ4oAALzAQACX1eZAAHI5jbpFQE9bAEAB20AAzYE",
    "WILD_DRAW_FOUR": "AAMCBAADGQEAARlLGmkwDIs0VGlJ9SkY76PK3-7ID_EYAAL1AQACX1eZAAHXOgABZUCgVkkBAAdtAAM2BA",
    "WILD_MYSTERY": "AAMCBAADGQEAARlMQGkwFpvktPnRl3mzIzQCHhP6ejExAALEAgACX1eZAAGi2Qy93IIQwgEAB20AAzYE",     # “?” card
    "SWAP": "AAMCBAADGQEAARlMTWkwFuN6wsT9kZsfHe-gNgi4TNziAAL6AgACX1eZAAFuilR5QnD-VwEAB20AAzYE",
    "STACK": "AAMCBAADGQEAARlMS2kwFtXj8KsI1enxoU5C5ha2yzu-AAL4AgACX1eZAAH-TdXSlvEa2wEAB20AAzYE",
    "PASS": "AAMCBAADGQEAARlMSWkwFslGpj5xcAHh0DmOU_UFZJKUAALOAgACX1eZAAHec7yiXsSGYwEAB20AAzYE",
    "DRAW": "AAMCBAADGQEAARlMRGkwFrYBmAOZpjQnzylwOH3_tdBtAALMAgACX1eZAAH8oQKsIYONPAEAB20AAzYE"
}

# -------------------------
# Helpers
# -------------------------
COLOR_LETTER_TO_NAME = {"R": "RED", "G": "GREEN", "B": "BLUE", "Y": "YELLOW"}
SPECIAL_NAME_MAP = {
    "SKIP": "SKIP",
    "REV": "REVERSE",
    "+2": "DRAW_TWO",
    # wilds handled separately
}

def card_code_to_sticker_key(card_code: str) -> Optional[str]:
    """
    Convert an internal card code (like 'B_5', 'R_SKIP', 'WILD', 'W4') to a STICKER_MAP key.
    Returns e.g. 'BLUE_5', 'RED_SKIP', 'WILD_DRAW_FOUR' or None if cannot convert.
    """
    card_code = card_code.strip()
    if card_code in ("WILD", "WILD_CARD", "W"):
        return "WILD"
    if card_code in ("W4", "WILD+4", "WILD_DRAW4"):
        return "WILD_DRAW_FOUR"

    if "_" not in card_code:
        return None

    color_letter, val = card_code.split("_", 1)
    color_name = COLOR_LETTER_TO_NAME.get(color_letter.upper())
    if not color_name:
        return None

    # numeric 0-9
    if val.isdigit():
        return f"{color_name}_{val}"

    # special variants
    val = val.upper()
    if val in SPECIAL_NAME_MAP:
        return f"{color_name}_{SPECIAL_NAME_MAP[val]}"

    # support some alternate names
    if val in ("REVERSE", "REV"):
        return f"{color_name}_REVERSE"
    if val in ("SKIP", "BLOCK"):
        return f"{color_name}_SKIP"
    if val in ("+2", "DRAW_TWO", "D2"):
        return f"{color_name}_DRAW_TWO"

    return None

def get_sticker_file_id(card_code: str) -> Optional[str]:
    """
    Return the sticker file_id for a given card_code (e.g. "B_5", "R_SKIP", "W4").
    If mapping missing, returns None.
    """
    key = card_code_to_sticker_key(card_code)
    if not key:
        return None
    return STICKER_MAP.get(key)

def build_full_cardfile_map() -> Dict[str, Optional[str]]:
    """
    Build mapping for the standard UNO deck codes -> sticker file_id (or None if missing).
    Useful to validate how many card codes are unmapped.
    """
    colors = ["R", "G", "B", "Y"]
    values = ["0","1","2","3","4","5","6","7","8","9","SKIP","REV","+2"]
    result: Dict[str, Optional[str]] = {}
    for c in colors:
        # zero (single)
        code = f"{c}_0"
        result[code] = get_sticker_file_id(code)
        for v in values[1:]:
            code = f"{c}_{v}"
            # each non-zero has two copies in deck logically, but mapping is same file id
            result[code] = get_sticker_file_id(code)
    # wilds
    result["WILD"] = get_sticker_file_id("WILD")
    result["W4"] = get_sticker_file_id("W4")
    return result

def validation_report() -> Tuple[int, int, List[str]]:
    """
    Return (mapped_count, missing_count, missing_keys_list)
    """
    full = build_full_cardfile_map()
    missing = [k for k, v in full.items() if v is None]
    return (len(full) - len(missing), len(missing), missing)

# -------------------------
# Example usage (commented)
# -------------------------
# from uno_card import get_sticker_file_id, card_code_to_sticker_key, validation_report
# fid = get_sticker_file_id("B_5")   # returns sticker file_id or None
# key = card_code_to_sticker_key("R_SKIP")  # "RED_SKIP"
# mapped, missing_count, missing_keys = validation_report()
# print("mapped:", mapped, "missing:", missing_count)
