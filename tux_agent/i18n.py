"""Status-bar text in English and Turkish. Picked from --lang, else $LANG / $LC_ALL."""

import os

TEXT = {
    "en": {
        "idle": "idle", "think": "thinking", "type": "writing code", "read": "reading files",
        "bash": "running commands", "web": "searching the web", "coffee": "getting coffee",
        "rest": "resting", "wait": "needs you!", "leave": "leaving",
        "quit": "q: quit",
        "waiting": "waiting for a Claude Code session…",
        "demo": "demo", "manual": "manual",
        "keys": "arrows: walk · t/r/b/w/c/s/a/l: actions · space: demo",
    },
    "tr": {
        "idle": "boşta", "think": "düşünüyor", "type": "kod yazıyor", "read": "dosya okuyor",
        "bash": "komut çalıştırıyor", "web": "internette arıyor", "coffee": "kahve alıyor",
        "rest": "dinleniyor", "wait": "onay bekliyor!", "leave": "çıkıyor",
        "quit": "q: çık",
        "waiting": "Claude Code oturumu bekleniyor…",
        "demo": "demo", "manual": "manuel",
        "keys": "oklar: yürü · t/r/b/w/c/s/a/l: eylem · boşluk: demo",
    },
}


def detect() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        if value:
            return "tr" if value.lower().startswith("tr") else "en"
    return "en"
