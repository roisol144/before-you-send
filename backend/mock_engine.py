"""Deterministic heuristic mock analyzer (no ML)."""
import re

LABELS = ["friendly", "neutral", "passive-aggressive", "angry", "anxious"]

LANGS = [  # (regex on script, code, name, flag)
    (r"[֐-׿]", "he", "Hebrew", "🇮🇱"),
    (r"[؀-ۿ]", "ar", "Arabic", "🇸🇦"),
    (r"[぀-ヿ]", "ja", "Japanese", "🇯🇵"),
    (r"[가-힯]", "ko", "Korean", "🇰🇷"),
    (r"[一-鿿]", "zh", "Chinese", "🇨🇳"),
    (r"[ऀ-ॿ]", "hi", "Hindi", "🇮🇳"),
    (r"[฀-๿]", "th", "Thai", "🇹🇭"),
    (r"[Ͱ-Ͽ]", "el", "Greek", "🇬🇷"),
    (r"[Ѐ-ӿ]", "ru", "Russian", "🇷🇺"),
]
KEYWORDS = {
    "es": ("Spanish", "🇪🇸", "hola gracias por favor que el la los es está muy pero como estoy con para una".split()),
    "fr": ("French", "🇫🇷", "bonjour merci je suis les des est très pas vous nous avec pour une mais".split()),
    "de": ("German", "🇩🇪", "hallo danke ich bin nicht und der die das ist sehr aber mit für ein bitte".split()),
    "pt": ("Portuguese", "🇵🇹", "olá obrigado não você uma para com muito estou mas".split()),
    "it": ("Italian", "🇮🇹", "ciao grazie sono non che per una molto ma con gli è".split()),
    "en": ("English", "🇬🇧", "the and is you to of i it that this for with are not have".split()),
}
FLAGS = {"he": "🇮🇱"}

FRIENDLY = "thanks thank love great awesome appreciate happy glad please wonderful amazing 😊 ❤ 🙏 :) hope lovely cheers".split()
ANGRY = ("hate stupid idiot useless shut furious ridiculous unacceptable worst sick of "
         "damn hell wtf terrible disgusting pathetic incompetent never again !!!").split()
PASSIVE = ["as per my last", "per my last", "fine.", "whatever", "no worries", "if you say so", "as i already",
           "as i mentioned", "just saying", "not sure why", "obviously", "sure, whatever", "thanks for nothing",
           "kindly", "i guess", "must be nice", "again,", "no offense", "with all due respect"]
ANXIOUS = ["worried", "sorry", "nervous", "afraid", "anxious", "hope that's ok", "hope this is ok", "is that ok",
           "not sure", "maybe", "?!", "i apologize", "apologies", "stress", "scared", "urgent", "please don't be mad",
           "just checking", "sorry to bother"]
INFORMAL = "hey yo lol omg gonna wanna gotta yeah yep nope dude u ur thx pls btw haha".split()
FORMAL = "dear sincerely regards kindly furthermore therefore please pursuant hereby respectfully cordially".split()


def detect_language(text):
    for pat, code, name, flag in LANGS:
        if re.search(pat, text):
            return {"code": code, "name": name, "flag": flag}
    words = re.findall(r"[a-zA-ZÀ-ÿ']+", text.lower())
    best, bs = "en", 0
    for code, (_, _, kws) in KEYWORDS.items():
        s = sum(1 for w in words if w in kws)
        if code != "en":
            s += 0.5 if s else 0
        if s > bs:
            best, bs = code, s
    if re.search(r"[ñ¿¡]", text.lower()) and bs < 2:
        best = "es"
    name, flag, _ = KEYWORDS[best]
    return {"code": best, "name": name, "flag": flag}


def _count(text, terms):
    return sum(text.count(t) for t in terms)


def analyze(text):
    lang = detect_language(text)
    raw = {l: 0.0 for l in LABELS}
    low = text.lower()
    words = re.findall(r"\w+", low)
    if not text.strip():
        return _out({"neutral": 1.0, **{l: 0 for l in LABELS if l != "neutral"}}, 3.0, 0.0, lang)
    letters = [c for c in text if c.isalpha()]
    caps = sum(c.isupper() for c in letters) / len(letters) if len(letters) > 4 else 0
    excl = text.count("!")
    fr = sum(1 for w in words if w in FRIENDLY) + _count(low, ["😊", "❤", "🙏", ":)"])
    an = sum(1 for w in words if w in ANGRY) + _count(low, ["!!!", "sick of", "never again"])
    pa = _count(low, PASSIVE)
    ax = _count(low, ANXIOUS)
    raw["friendly"] = fr * 1.5
    raw["angry"] = an * 2 + (2 if caps > 0.6 else 0) + max(0, excl - 1) * 0.5
    raw["passive-aggressive"] = pa * 2
    raw["anxious"] = ax * 1.5
    raw["neutral"] = 1.0
    total = sum(raw.values())
    scores = {k: v / total for k, v in raw.items()}
    formal = 3.0 + 0.6 * sum(1 for w in words if w in FORMAL) - 0.7 * sum(1 for w in words if w in INFORMAL)
    formal += 0.5 if text.strip().endswith(".") and len(words) > 12 else 0
    formal -= 0.5 * (caps > 0.6) + 0.2 * excl
    formal = max(1.0, min(5.0, formal))
    risk = 0.85 * scores["angry"] + 0.6 * scores["passive-aggressive"] + 0.15 * scores["anxious"] - 0.2 * scores["friendly"]
    if an or pa:
        risk += 0.1
    return _out(scores, formal, max(0.0, min(1.0, risk)), lang)


def _out(scores, formal, risk, lang):
    label = max(LABELS, key=lambda l: (scores[l], l == "neutral"))
    return {
        "tone": {"label": label, "confidence": round(scores[label], 3),
                 "scores": {k: round(v, 4) for k, v in scores.items()}},
        "formality": {"score": round(formal, 2), "confidence": 0.5},
        "fight_risk": round(risk, 3),
        "language": lang,
    }
