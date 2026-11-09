#!/usr/bin/env python3
"""SEC EDGAR helper (free, no key). Read-only.

  edgar.py filings TICKER [FORMS] [N]   recent filings, e.g. filings MU 10-K,10-Q,8-K 15
  edgar.py insiders TICKER [N]          recent Form 4 insider filings (links)
  edgar.py facts TICKER                 key reported figures from XBRL, last 6 periods
  edgar.py doc URL [MAXCHARS]           fetch a filing document as plain text
  edgar.py current FORM [N]             newest filings of FORM across the whole market,
                                        with ticker and 8-K items, e.g. current 8-K 100,
                                        current "SC 13D", current 10-12B (spin-offs);
                                        current 4 N lists open-market insider BUYS
                                        found in the newest N Form 4s
"""
import datetime, json, re, sys, html, time, urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "personal-research research@example.com"}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()

def cik(ticker):
    for line in get("https://www.sec.gov/include/ticker.txt").decode().splitlines():
        t, c = line.split("\t")
        if t == ticker.lower():
            return int(c)
    sys.exit(f"{ticker}: not found in SEC ticker list")

def submissions(ticker):
    c = cik(ticker)
    return c, json.loads(get(f"https://data.sec.gov/submissions/CIK{c:010d}.json"))

def filings(ticker, forms="10-K,10-Q,8-K", n=15):
    c, s = submissions(ticker)
    want = set(forms.split(","))
    r = s["filings"]["recent"]
    print(f"{s['name']} (CIK {c})")
    shown = 0
    for i, form in enumerate(r["form"]):
        if form in want:
            acc = r["accessionNumber"][i].replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{c}/{acc}/{r['primaryDocument'][i]}"
            items = r.get("items", [""] * len(r["form"]))[i]
            print(f"{r['filingDate'][i]}  {form:6} {('items ' + items) if items else '':18} {url}")
            shown += 1
            if shown >= n:
                break

def insiders(ticker, n=15):
    filings(ticker, "4", n)

FACTS = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "GrossProfit",
         "OperatingIncomeLoss", "NetIncomeLoss", "CashAndCashEquivalentsAtCarryingValue",
         "LongTermDebt", "NetCashProvidedByUsedInOperatingActivities",
         "PaymentsToAcquirePropertyPlantAndEquipment", "WeightedAverageNumberOfDilutedSharesOutstanding"]

def facts(ticker):
    c = cik(ticker)
    f = json.loads(get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{c:010d}.json"))["facts"].get("us-gaap", {})
    for name in FACTS:
        if name not in f:
            continue
        unit = next(iter(f[name]["units"]))
        rows = [x for x in f[name]["units"][unit] if x.get("form") in ("10-K", "10-Q")]
        if not rows or max(x["end"] for x in rows) < str(datetime.date.today().year - 1):
            continue  # tag no longer reported; the company switched to a different concept
        seen, out = set(), []
        for x in sorted(rows, key=lambda x: x["end"], reverse=True):
            key = (x.get("start"), x["end"])
            if key in seen:
                continue
            seen.add(key)
            out.append(f"{x.get('start','')}..{x['end']} {x['form']} fy{x.get('fy')}{x.get('fp')}: {x['val']:,}")
            if len(out) >= 6:
                break
        print(f"\n{name} ({unit})\n  " + "\n  ".join(out))

# EDGAR renamed these in 2025; the old names now match nothing.
RENAMED = {"SC 13D": "SCHEDULE 13D", "SC 13G": "SCHEDULE 13G"}

def current(form="8-K", n=100):
    """Market-wide feed of the newest filings: the way to find companies nobody is watching."""
    form = RENAMED.get(form.upper(), form)
    if form == "4":
        return insider_buys(int(n))
    tickers = {v["cik_str"]: v["ticker"] for v in json.loads(get("https://www.sec.gov/files/company_tickers.json")).values()}
    url = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type="
           f"{urllib.request.quote(form)}&owner=include&count={int(n)}&output=atom")
    feed = get(url).decode("utf-8", "ignore")
    for e in re.findall(r"(?s)<entry>(.*?)</entry>", feed):
        title = html.unescape(re.search(r"<title>(.*?)</title>", e).group(1))
        m = re.match(r"(.+?) - (.*?) \((\d+)\) \((\w+)\)", title)
        if not m or m.group(4) not in ("Filer", "Subject"):
            continue
        f, name, c = m.group(1), m.group(2), int(m.group(3))
        if f not in (form, form + "/A"):
            continue  # the feed prefix-matches: type=4 also returns 424B2, 485BPOS, ...
        if c not in tickers:
            continue  # no listed stock (funds, private issuers, individuals)
        summary = html.unescape(re.search(r"(?s)<summary[^>]*>(.*?)</summary>", e).group(1))
        items = ",".join(re.findall(r"Item (\d\.\d\d)", summary))
        date = re.search(r"<updated>(.*?)T", e).group(1)
        link = re.search(r'<link[^>]*href="([^"]+)"', e).group(1)
        print(f"{date}  {tickers[c]:6} {f:14} {('items ' + items) if items else '':24} {name[:40]:40} {link}")

def insider_buys(n=200, days=5):
    """Open-market insider purchases (Form 4, transaction code P) across the market.

    Scans up to n of the newest Form 4s from EDGAR full-text search, which filters
    on the exact form (the getcurrent feed does not), and reads each filing's XML.
    """
    listed = {v["cik_str"] for v in json.loads(get("https://www.sec.gov/files/company_tickers.json")).values()}
    scanned = found = 0
    day = datetime.date.today()
    for _ in range(days * 2):  # calendar days, enough to cover `days` business days
        if scanned >= n:
            break
        if day.weekday() < 5:
            start = 0
            while scanned < n:
                q = (f"https://efts.sec.gov/LATEST/search-index?forms=4&dateRange=custom"
                     f"&startdt={day}&enddt={day}&from={start}")
                hits = json.loads(get(q))["hits"]["hits"]
                if not hits:
                    break
                for h in hits:
                    if scanned >= n:
                        break
                    acc, fname = h["_id"].split(":", 1)
                    ciks = [int(c) for c in h["_source"]["ciks"]]
                    issuer = next((c for c in ciks if c in listed), None)
                    if issuer is None:
                        continue  # issuer has no listed stock
                    scanned += 1
                    url = f"https://www.sec.gov/Archives/edgar/data/{issuer}/{acc.replace('-', '')}/{fname}"
                    time.sleep(0.12)  # SEC asks for at most 10 requests a second
                    try:
                        x = ET.fromstring(get(url))
                    except Exception:
                        continue
                    line = form4_buy(x)
                    if line:
                        found += 1
                        print(f"{h['_source']['file_date']}  {line}  {url}")
                start += len(hits)
        day -= datetime.timedelta(days=1)
    print(f"-- {found} open-market buys in {scanned} Form 4s at listed companies")

def form4_buy(x):
    """One summary line if this Form 4 reports open-market purchases, else None."""
    val = lambda e, p: (e.findtext(p) or "").strip()
    shares = dollars = 0.0
    for t in x.iter("nonDerivativeTransaction"):
        if val(t, "transactionCoding/transactionCode") != "P":
            continue
        s = float(val(t, "transactionAmounts/transactionShares/value") or 0)
        p = float(val(t, "transactionAmounts/transactionPricePerShare/value") or 0)
        shares += s
        dollars += s * p
    if not shares:
        return None
    rel = x.find("reportingOwner/reportingOwnerRelationship")
    role = ""
    if rel is not None:
        role = val(rel, "officerTitle") or ("Director" if val(rel, "isDirector") in ("1", "true") else
               "10% owner" if val(rel, "isTenPercentOwner") in ("1", "true") else "")
    price = f"~${dollars / shares:,.2f}" if dollars else "price n/a"
    amount = f"${dollars:>13,.0f}" if dollars else f"{'?':>14}"
    return (f"{val(x, 'issuer/issuerTradingSymbol').upper():6} {amount}  "
            f"{shares:>11,.0f} sh @ {price:10}  "
            f"{val(x, 'reportingOwner/reportingOwnerId/rptOwnerName')[:28]:28} {role[:24]:24}")

def doc(url, maxchars=60000):
    t = get(url).decode("utf-8", "ignore")
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    print(re.sub(r"\s+", " ", t)[: int(maxchars)])

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, *args = sys.argv[1:]
    {"filings": lambda: filings(args[0], *(args[1:2] or []), *(map(int, args[2:3]))),
     "insiders": lambda: insiders(args[0], *map(int, args[1:2])),
     "facts": lambda: facts(args[0]),
     "doc": lambda: doc(*args),
     "current": lambda: current(*args)}[cmd]()
