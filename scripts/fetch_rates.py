#!/usr/bin/env python3
"""Pobiera aktualne dane do aplikacji i zapisuje je w data/rates.json.

Źródła:
  - GUS, API SDP: wskaźnik cen towarów i usług konsumpcyjnych r/r (inflacja CPI)
  - NBP: stopy procentowe (stopy_procentowe.xml)
  - Ministerstwo Finansów: bieżąca oferta obligacji oszczędnościowych

Każde źródło jest pobierane osobno. Gdy jedno zawiedzie albo zwróci wartość
spoza rozsądnego zakresu, w pliku zostaje poprzednia wartość z jej datą.
Tylko biblioteka standardowa, żeby workflow nie musiał niczego instalować.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# ─── Constants ───
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "rates.json"
TIMEOUT_S = 30
USER_AGENT = "fin-edu-rates/1.0 (+https://github.com/workszop/fin-edu)"
GUS_CPI_URL = "https://api-sdp.stat.gov.pl/api/indicators/indicator-data-indicator?id-wskaznik=2728&id-rok={year}&lang=pl"
GUS_CPI_PAGE = "https://stat.gov.pl/obszary-tematyczne/ceny-handel/wskazniki-cen/wskazniki-cen-towarow-i-uslug-konsumpcyjnych-pot-inflacja-/"
GUS_FIRST_MONTH_PERIOD = 247  # id-okres 247 = styczeń, 258 = grudzień
NBP_URL = "https://static.nbp.pl/dane/stopy/stopy_procentowe.xml"
NBP_PAGE = "https://nbp.pl/polityka-pieniezna/decyzje-rpp/podstawowe-stopy-procentowe-nbp/"
MF_URL = "https://www.gov.pl/web/finanse/biezaca-oferta2"
BOND_SYMBOLS = ("OTS", "ROR", "DOR", "TOS", "COI", "EDO", "ROS", "ROD")
FIXED_BONDS = ("OTS", "TOS")
PL_MONTHS = {"styczeń": 1, "luty": 2, "marzec": 3, "kwiecień": 4, "maj": 5, "czerwiec": 6, "lipiec": 7,
             "sierpień": 8, "wrzesień": 9, "październik": 10, "listopad": 11, "grudzień": 12}
# Sanity ranges in percent. A value outside means the source changed format.
RANGE_INFLATION = (-5.0, 30.0)
RANGE_NBP = (0.0, 25.0)
RANGE_BOND = (0.0, 20.0)
RANGE_MARGIN = (0.0, 5.0)


# ─── Helpers ───
def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as res:
        return res.read()


def pl_num(s: str) -> float:
    return float(s.replace(" ", "").replace(" ", "").replace(",", "."))


def in_range(v: float, rng: tuple[float, float], what: str) -> float:
    if not (rng[0] <= v <= rng[1]):
        raise ValueError(f"{what}={v} poza zakresem {rng}")
    return round(v, 2)


# ─── Sources ───
def fetch_inflation(today: dt.date) -> dict:
    rows = []
    for year in (today.year, today.year - 1):
        data = json.loads(get(GUS_CPI_URL.format(year=year)))
        if isinstance(data, list):
            rows += [(int(r["id-daty"]), int(r["id-okres"]) - GUS_FIRST_MONTH_PERIOD + 1, float(r["wartosc"]))
                     for r in data if r.get("wartosc") is not None]
        if rows:
            break
    if not rows:
        raise ValueError("GUS: brak danych")
    year, month, index = max(rows)
    if not 1 <= month <= 12:
        raise ValueError(f"GUS: nieznany okres {month}")
    return {"value": in_range(index - 100, RANGE_INFLATION, "inflacja"), "period": f"{year}-{month:02d}",
            "source": "GUS", "url": GUS_CPI_PAGE}


def fetch_nbp() -> dict:
    root = ET.fromstring(get(NBP_URL).decode("utf-8-sig"))
    rates = {p.get("id"): p for p in root.iter("pozycja")}
    out = {"source": "NBP", "url": NBP_PAGE}
    for key, pid in (("ref", "ref"), ("lombard", "lom"), ("deposit", "dep")):
        out[key] = in_range(pl_num(rates[pid].get("oprocentowanie")), RANGE_NBP, f"NBP {pid}")
    out["since"] = rates["ref"].get("obowiazuje_od")
    dt.date.fromisoformat(out["since"])  # format check
    return out


def page_text(raw: bytes) -> str:
    s = raw.decode("utf-8", "replace")
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|h\d|li|div)>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"[ \t ]+", " ", s)


def fetch_bonds() -> dict:
    text = page_text(get(MF_URL))
    m = re.search(r"Oferta na (\w+) (\d{4})", text)
    if not m or m.group(1).lower() not in PL_MONTHS:
        raise ValueError("MF: brak nagłówka oferty")
    offer = f"{m.group(2)}-{PL_MONTHS[m.group(1).lower()]:02d}"
    # Sekcja każdej obligacji zaczyna się od jej serii, np. "EDO1136", a kończy na następnej serii.
    heads = list(re.finditer(r"\b(" + "|".join(BOND_SYMBOLS) + r")(\d{4})\b(?=\s*\n)", text))
    items = {}
    for i, h in enumerate(heads):
        sym = h.group(1)
        if sym in items:
            continue
        part = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        pct = r"(\d+,\d+)\s*%"
        item = {"series": sym + h.group(2)}
        if sym in FIXED_BONDS:
            r = re.search(r"[Ww]ynosi\s+" + pct, part)
            if not r:
                continue
            item["rate"] = in_range(pl_num(r.group(1)), RANGE_BOND, sym)
        else:
            r = re.search(r"(?:wynosi|równe)\s+" + pct, part)
            mg = re.search(r"marży w wysokości\s+" + pct, part)
            if not r or not mg:
                continue
            item["first"] = in_range(pl_num(r.group(1)), RANGE_BOND, sym)
            item["margin"] = in_range(pl_num(mg.group(1)), RANGE_MARGIN, sym + " marża")
        items[sym] = item
    if len(items) < 6:
        raise ValueError(f"MF: rozpoznano tylko {sorted(items)}")
    return {"offer": offer, "items": items, "source": "Ministerstwo Finansów", "url": MF_URL}


# ─── Main ───
def main() -> int:
    today = dt.date.today()
    old = json.loads(OUT_PATH.read_text("utf-8")) if OUT_PATH.exists() else {}
    new = dict(old)
    errors = []
    for key, fn in (("inflation", lambda: fetch_inflation(today)), ("nbp", fetch_nbp), ("bonds", fetch_bonds)):
        try:
            new[key] = fn()
        except Exception as e:  # noqa: BLE001 - każde źródło może zawieść inaczej
            errors.append(f"{key}: {e}")
            print(f"WARN {key}: {e}", file=sys.stderr)
    if len(errors) == 3 and not old:
        return 1
    strip = lambda d: {k: v for k, v in d.items() if k != "updated"}
    if strip(new) != strip(old) or not old:
        new["updated"] = today.isoformat()
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUT_PATH.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n", "utf-8")
        print("rates.json zaktualizowany")
    else:
        print("bez zmian")
    return 0


if __name__ == "__main__":
    sys.exit(main())
