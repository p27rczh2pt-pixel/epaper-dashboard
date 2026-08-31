# Icon sources

| File | Source | License |
|---|---|---|
| `pihole.png` | [Simple Icons](https://simpleicons.org/?q=pihole) — `pihole.svg` | CC0 1.0 (public domain) |
| `raspberrypi.png` | [Simple Icons](https://simpleicons.org/?q=raspberrypi) — `raspberrypi.svg` | CC0 1.0 (public domain) |
| `globe.png` | [Feather Icons](https://feathericons.com/?query=globe) — `globe.svg` | MIT (Cole Bemis) |
| `cpu.png` | [Feather Icons](https://feathericons.com/?query=cpu) — `cpu.svg` | MIT (Cole Bemis) |

Simple Icons' CC0 dedication covers the icon artwork itself; the brand
names/logos it depicts (Pi-hole, Raspberry Pi) may still be trademarks of
their respective owners. Used here only to represent those exact products
on a personal monitoring dashboard — not for endorsement or resale.

Source SVGs converted to flat black-on-transparent 40x40 PNGs via
`GdkPixbuf`/librsvg — see `convert_icons.py` in this directory to
regenerate. Feather's icons use `stroke="currentColor"`, pinned to black
explicitly during conversion rather than relying on a renderer default.

Formerly pasted onto the e-paper canvas using the alpha channel as a mask
(`display/render.py`, since removed); now served from `app/static/icons/`
and colorized per-page in `dashboard.html` via CSS `mask-image`, which
uses the same alpha channel the same way.

Full license texts: [Simple Icons (CC0)](https://github.com/simple-icons/simple-icons/blob/develop/LICENSE.md),
[Feather (MIT)](https://github.com/feathericons/feather/blob/main/LICENSE).
