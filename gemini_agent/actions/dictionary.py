from enum import Enum

class Language(Enum):
    ENG = "en"
    RUS = "ru"
    KAZ = "kk"

# All words should be lowercase.
class Dictionary:
    _dictionary = {
        "hi": Language.ENG,
        "no": Language.ENG,
        "ok": Language.ENG,
        "cu": Language.ENG,
        "y": Language.ENG,
        "да": Language.RUS,
        "д": Language.RUS,
        "ку": Language.RUS,
        "ок": Language.RUS,
        "неа": Language.RUS,
        "иә": Language.KAZ,
        "салем": Language.KAZ
    }

    @classmethod
    def get_lang(cls, key: str):
        if key in cls._dictionary:
            return True, cls._dictionary[key]
        return False, None
