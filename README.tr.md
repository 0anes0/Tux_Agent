<div align="center">

# 🐧 Tux_Agent

**Claude Code ajanların, piksel bir ofiste yaşayan Tux penguenleri olarak, doğrudan terminalinde.**

[English](README.md) · [Türkçe](README.tr.md)

![Tux ofisinde çalışan üç Claude Code oturumu](docs/demo.gif)

</div>

Her Claude Code oturumunun kendi Tux'u olur. Claude dosya okurken Tux kitaplığa yürür.
Kod düzenlerken masasına oturur ve monitörde kod akar. Senden onay beklerken başında **!**
ile sana el sallar. İş bitince halıya oturup mola verir.

Tarayıcı yok, editör eklentisi yok: ofis doğrudan terminaline, Claude Code'un yanına çizilir.

## Özellikler

- [Kitty grafik protokolü](https://sw.kovidgoyal.net/kitty/graphics-protocol/) ile **terminalde gerçek pikseller** (Kitty, WezTerm, Ghostty). Truecolor destekleyen her terminalde `▀` karakterli yedek mod
- **Oturum başına bir Tux**: birden fazla Claude Code oturumu açarsan her birinin kendi penguenini ve masasını görürsün
- **Canlı**: Claude Code [hook'ları](https://code.claude.com/docs/en/hooks) olayları yerel bir Unix socket üzerinden anında iletir
- **Claude'a sıfır yük**: hook'lar arka planda (async) çalışır, ~20 ms sürer, hiçbir şey yazdırmaz; Tux_Agent kapalıyken hiçbir şey yapmaz
- **Gizlilik**: Claude Code'dan sadece olay adı, araç adı, oturum kimliği ve klasör adı çıkar. Dosya içeriği ya da komutlar asla gönderilmez, gidenler de yalnızca bilgisayarındaki bir socket'e gider
- Mobilyaların etrafından yol bulma, göz kırpma, yanıp sönen sunucu LED'leri, Türkçe ve İngilizce durum satırı

## Tux ne yapar

| Claude Code | Tux |
|---|---|
| Oturum açıldı / mesaj gönderdin | masasına gidip düşünür |
| `Read`, `Grep`, `Glob` | kitaplıkta kitap okur |
| `Edit`, `Write` | masada yazar, monitörde kod akar |
| `Bash` | sunucu dolabıyla uğraşır |
| `WebSearch`, `WebFetch` | pencereden dışarı bakar |
| Onay isteği | durup el sallar, başında **!** balonu çıkar |
| İş bitti (`Stop`) | halıya oturup dinlenir |
| Oturum kapandı | kapıdan çıkar |

## Gereksinimler

- Linux (diğer Unix benzeri sistemlerde de büyük ihtimalle çalışır ama denenmedi)
- Python 3.10+
- [Claude Code](https://code.claude.com)
- En iyi görüntü için **Kitty**, **WezTerm** ya da **Ghostty**. Diğer truecolor terminaller daha düşük çözünürlüklü yedek modu kullanır. Kitty modu henüz tmux içinde çalışmıyor.

## Kurulum

```sh
# 1. programı kur (uv ya da pipx)
uv tool install git+https://github.com/0anes0/Tux_Agent
# veya: pipx install git+https://github.com/0anes0/Tux_Agent

# 2. hook'ları ~/.claude/settings.json'a ekle (önce yedek alınır)
tux-agent install
```

Ya da doğrudan klondan:

```sh
git clone https://github.com/0anes0/Tux_Agent && cd Tux_Agent
pip install --user pillow
python3 -m tux_agent install
```

## Kullanım

Bir terminal penceresinde ofisi aç, diğerinde Claude Code'u her zamanki gibi kullan:

```sh
tux-agent            # ya da: python3 -m tux_agent
```

Kitty'de Claude Code'un hemen yanında bir bölme çok iyi olur: `ctrl+shift+enter` mevcut sekmede
yeni bir pencere açar. Görüntü, verilen alanı dolduracak şekilde büyür.

Hiç oturum yokken ofiste bir demo Tux dolaşır ve onu sen yönetebilirsin:

| Tuş | Eylem |
|---|---|
| ok tuşları | yürü |
| `t` `r` `b` `w` | yaz · oku · bash · pencere |
| `c` `s` `a` `l` | kahve · otur · onay iste (el salla) · çık |
| `boşluk` | demo modunu aç/kapat |
| `q` / `esc` | çıkış |

Seçenekler:

```
--backend {kitty,halfblock}   çizim yöntemini zorla (varsayılan: otomatik)
--lang {en,tr}                durum satırı dili (varsayılan: $LANG'a göre)
--gif DOSYA                   demoyu terminal yerine GIF olarak kaydet
```

## Nasıl çalışıyor

```
 Claude Code ──hook (async)──► tux_agent/hook.py ──Unix datagram──► tux-agent
                                                   $XDG_RUNTIME_DIR/        │
                                                   tux-agent.sock           ▼
                                              ofis + Tux'lar RGBA tampona çizilir
                                              → Kitty grafik protokolü / yarım bloklar
```

- `tux_agent/hook.py`: Claude Code'un her olayda çalıştırdığı, sadece standart kütüphaneyi kullanan küçük script; veriyi kırpıp gönderir
- `tux_agent/events.py`: socket dinleyicisi ve olay → eylem eşlemesi
- `tux_agent/agent.py`: Tux'un durum makinesi, BFS yol bulma ve animasyonlar
- `tux_agent/office.py`: tamamen kodla çizilen ofis
- `tux_agent/backends.py`: Kitty (zlib sıkıştırmalı, çift tamponlu, titremesiz) ve yarım blok çiziciler

## Kaldırma

```sh
tux-agent uninstall      # sadece Tux_Agent'ın hook'larını siler, diğer ayarlara dokunmaz
uv tool uninstall tux-agent
```

## Yol haritası

- [ ] Subagent'lar için yavru Tux'lar
- [ ] Her Tux'a farklı renk ve aksesuar
- [ ] Dar ve uzun pencereler için düzen
- [ ] Ofis editörü
- [ ] Sixel desteği

## Emeği geçenler ve lisans

- Kod: **GNU GPL v3**, bkz. [`LICENSE`](LICENSE).
- Tux sprite'ları: **Kelvin Shadewing**'in [*Tux – Kyrodian Legends Style*](https://opengameart.org/content/tux-kyrodian-legends-style)
  çalışması (CC-BY-SA 4.0 / GPL 3.0). Tux'un orijinali **Larry Ewing**'e aittir ve The GIMP ile çizilmiştir.
  Ayrıntılar: [`tux_agent/assets/CREDITS.md`](tux_agent/assets/CREDITS.md).
- İlham kaynağı: aynı şeyi VS Code içinde yapan [Pixel Agents](https://github.com/pablodelucca/pixel-agents).

Tux_Agent bir hayran projesidir ve Anthropic ile bağlantılı değildir.
