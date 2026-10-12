# Tux_Agent — Yol Haritası

Claude Code ajanlarını piksel-art bir ofiste dolaşan **Tux** penguenleri olarak gösteren,
**doğrudan terminalde** çalışan bir görselleştirici. İlham: [Pixel Agents](https://github.com/pablodelucca/pixel-agents) (MIT, VS Code eklentisi).

Fark: Pixel Agents VS Code içinde çalışıyor. Tux_Agent ise düz Linux terminalinde çalışan
Claude Code'u izler ve ofisi **yine terminalde**, Claude Code'un yanındaki bir split/pencerede çizer.
Tarayıcı yok.

---

## Mimari

```
┌──────────── Kitty penceresi ────────────────────────────┐
│  Claude Code (sol split)    │  tux-agent (sağ split)     │
│                             │  piksel ofis + Tux'lar     │
└─────────────┬───────────────┴──────────────▲────────────┘
              │ hooks: SessionStart, PreToolUse, PostToolUse,
              │        Notification, Stop, SubagentStop ...
              ▼                              │
        hooks/tux-hook ── Unix socket ───────┘
```

- **Olay kaynağı:** Claude Code hook'ları (resmi, kararlı arayüz). Yedek plan:
  `~/.claude/projects/**/*.jsonl` transcript dosyalarını izlemek (Pixel Agents bunu yapıyor).
- **tux-agent (TUI):** tek bir süreç. Hem olayları Unix socket'ten dinler hem ofisi çizer.
  Ayrı bir sunucu ya da WebSocket gerekmez.
- **Oyun döngüsü:** sabit FPS, ızgara tabanlı harita, BFS yol bulma, karakter durum makinesi.
  Her karede önce bellekteki bir **piksel tamponuna** (RGBA) çizilir, sonra bir *render backend*
  bunu terminale basar.

### Render backend'leri

| Backend          | Nasıl                                             | Nerede çalışır                         |
|------------------|---------------------------------------------------|----------------------------------------|
| **kitty** (ana)  | Kitty graphics protocol, gerçek piksel görüntü    | Kitty, WezTerm, Ghostty                |
| **halfblock**    | `▀` karakteri + truecolor, 1 hücre = 2 piksel     | Truecolor destekli her terminal        |
| sixel (belki)    | Sixel grafik                                      | foot, xterm, Konsole                   |

Kitty backend'de ofis tam çözünürlükte görünür. Halfblock ise 80×24'lük bir terminalde
yalnızca 80×48 piksel verir, bu yüzden yedek çözüm olarak kalır.

- **Dil:** Python + Pillow (sprite yükleme/kompozisyon), ek bağımlılık minimum.
  Performans yetmezse Go/Rust'a geçmek kolay, çünkü backend arayüzü basit.
- **Açılış:** `tux-agent` komutu ya da `kitty @ launch --location=vsplit tux-agent`
  ile Claude Code'un yanında otomatik split.

### Ajan durumu → Tux animasyonu

| Claude Code olayı            | Tux ne yapar                         |
|------------------------------|--------------------------------------|
| SessionStart                 | Kapıdan girer, boş masaya yürür      |
| Edit / Write                 | Masada klavyede yazar                |
| Read / Grep / Glob           | Kitap/kağıt okur                     |
| Bash                         | Sunucu dolabına gidip uğraşır        |
| WebSearch / WebFetch         | Pencereden dışarı / dürbünle bakar   |
| Notification (onay bekliyor) | Başının üstünde "!" balonu, el sallar|
| Stop (iş bitti)              | Kahve makinesine gider, dinlenir     |
| Subagent başladı             | Yanına küçük bir Tux yavrusu gelir   |
| SessionEnd                   | Kapıdan çıkar                        |

---

## Aşamalar

### Faz 0 — Araştırma ve varlıklar (assets)
- [x] Açık lisanslı Tux sprite'larını topla, lisanslarını `assets/CREDITS.md`'ye yaz
- [x] Bakış açısına karar ver: ofis için **üstten / 3/4 görünüm** gerekli.
      Bulunan Tux sprite'larının çoğu yandan görünüm (platform oyunu). Muhtemelen
      bunları referans alıp 4 yönlü kendi Tux'umuzu çizeceğiz.
- [x] Ofis tileset'i: şimdilik kodla çiziliyor (`office.py`), ileride gerçek tileset'e geçilebilir

### Faz 1 — Statik prototip
- [x] `tux_agent/`: piksel tamponu + kitty backend, ofis haritası + tek Tux, klavyeyle yürütme
- [x] Sprite sheet yükleme, yürüme/oturma/yazma animasyonları
- [x] halfblock backend (yedek)

### Faz 2 — Canlı bağlantı
- [x] Unix socket dinleyici (`$XDG_RUNTIME_DIR/tux-agent.sock`)
- [x] `hooks/`: Claude Code'un çağıracağı küçük script (socket'e JSON yollar, TUI kapalıysa sessizce geçer)
- [x] Gerçek bir Claude Code oturumunda Tux'un tepki verdiğini gör

### Faz 3 — Çoklu ajan ve cila
- [ ] Birden fazla oturum = birden fazla Tux (her birine farklı renk/aksesuar)
- [ ] Subagent'lar, konuşma balonları, ses (opsiyonel)
- [ ] Basit ofis editörü (masa/mobilya yerleştirme)

### Faz 4 — Yayın (beğenirsek)
- [x] README, GIF/demo videosu, kurulum scripti
- [x] Lisans dosyaları, GitHub'a push

---

## Lisans notları (önemli)

- **Kod:** GNU GPL v3 (repo oluşturulurken seçildi).
- **Görseller:** ayrı lisans. Örnek kaynaklar:
  - [Tux – Kyrodian Legends style](https://opengameart.org/content/tux-kyrodian-legends-style) — CC-BY-SA 4.0 / GPL 3.0
  - Worldmap Tux (Vaesea) — CC-BY-SA 4.0, üstten görünüm, ofise en uygun aday
  - SuperTux sprite'ları — GPL
  - Orijinal Tux (Larry Ewing) — kullanım serbest, kaynak göstermek şartıyla
- CC-BY-SA bir görselden türetilen sprite'lar da **CC-BY-SA** olmalı. Bu yüzden görseller
  `assets/` altında kendi `LICENSE`/`CREDITS` dosyalarıyla ayrı tutulacak.
- Pixel Agents'tan kod alırsak MIT telif bildirimini korumamız gerekir.

## Klasör yapısı

```
Tux_Agent/
├── tux_agent/            Python paketi
│   ├── app.py            ana döngü, sahne, CLI
│   ├── agent.py          Tux: durum makinesi, yol bulma, animasyon
│   ├── office.py         kodla çizilen ofis
│   ├── sprites.py        sprite sheet ve animasyonlar
│   ├── backends.py       kitty / halfblock çizim
│   ├── events.py         socket dinleyici, olay → eylem
│   ├── hook.py           Claude Code hook script'i
│   ├── install.py        tux-agent install / uninstall
│   ├── i18n.py           İngilizce / Türkçe metinler
│   └── assets/           paketle gelen sprite + CREDITS.md
├── art/                  kaynak çizimler (pakete girmez)
├── docs/demo.gif         README animasyonu (tools/demo_gif.py üretir)
└── tools/                yardımcı script'ler
```
