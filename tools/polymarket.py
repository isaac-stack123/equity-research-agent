#!/usr/bin/env python3
"""Paper forecasting log against Polymarket prices (public API, no key, no money). Read-only on Polymarket.

  polymarket.py list [TAG ...]            open markets in economy/Fed/inflation/finance tags (or the given
                                          tags) with liquidity >= $50k and at least 2 days to run: id, end
                                          date, liquidity, question. NO prices, on purpose.
  polymarket.py show ID                   one market's question and resolution rules. NO price.
  polymarket.py record ID PROB "REASON"   log our probability (0-1) that the market resolves YES. The
                                          market's YES price is fetched and stored at this moment, unseen.
  polymarket.py score                     fill in resolved outcomes, then compare our Brier score with the
                                          market's on every resolved forecast, and report the mechanical track.
  polymarket.py mech                      mechanical track (no judgment): paper-buy $1 of YES at the ask in every
                                          fixed-date economics market (Fed decision, data release, bracket) that
                                          ends in 5-9 days with YES priced 80-97%. Logged to mechanical.csv.

The mechanical track tests the one bias found in a study of ~3,000 resolved markets (2024-2026):
favorites priced 80-97% about a week out in fixed-date economics markets won more often than priced
(~+6-7% per $1 before costs). Early-closing markets ("hit $X", "by <date>") are excluded on purpose.

Prices are hidden from list/show so the forecast is our own, not an echo of the crowd. The log is
research/forecasts/forecasts.csv. Brier score = (probability - outcome)^2, outcome 1 for YES, 0 for NO;
lower is better; always saying 50% scores 0.25.
"""
import csv, datetime, json, os, re, sys, urllib.error, urllib.request

API = "https://gamma-api.polymarket.com"
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "research", "forecasts", "forecasts.csv")
FIELDS = ["logged_utc", "market_id", "question", "end_date", "our_p", "market_p", "reason", "outcome", "resolved_utc"]
MECH_LOG = os.path.join(os.path.dirname(LOG), "mechanical.csv")
MECH_FIELDS = ["logged_utc", "market_id", "question", "end_date", "entry_ask", "mid", "outcome", "resolved_utc"]
MECH_TAGS, MECH_DAYS, MECH_BAND = ["economy", "fed-rates", "inflation"], (5, 9), (0.80, 0.97)
DEFAULT_TAGS = ["economy", "fed-rates", "inflation", "finance"]
MIN_LIQUIDITY, MIN_DAYS = 50_000, 2

def get(path):
    req = urllib.request.Request(API + path, headers={"User-Agent": "Mozilla/5.0"})
    return json.load(urllib.request.urlopen(req, timeout=30))

def market(mid):
    # /markets?id= hides closed markets, so a resolved market would look missing; fetch it by path.
    try:
        return get(f"/markets/{mid}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            sys.exit(f"no market with id {mid}")
        raise

def yes_price(m):
    outcomes, prices = json.loads(m["outcomes"]), json.loads(m["outcomePrices"])
    if outcomes[:2] != ["Yes", "No"]:
        sys.exit(f"market {m['id']} is not a Yes/No market: {outcomes}")
    return float(prices[0])

def resolved(m):
    """1 or 0 once the market has closed on a final price, else None."""
    if not m.get("closed"):
        return None
    p = yes_price(m)
    return 1 if p >= 0.99 else 0 if p <= 0.01 else None

def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

def load(path=LOG):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))

def save(rows, path=LOG, fields=FIELDS):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def fixed_date(question, event_title, n_in_event):
    """Fed decisions, data releases and multi-outcome brackets settle on a known date. Markets that can
    close early ("hit $X", "by <date>") are not fixed-date and are excluded."""
    s = (question + " " + event_title).lower()
    if (re.search(r"\b(hit|hits|reach|reaches|dip|dips|touch)\b", s)
            or re.search(r"\bby (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|end of|\d{1,2}/|20\d\d)", s)
            or re.search(r"\b(in|during) 20\d\d\b", question.lower())):
        return False
    if re.search(r"\b(cpi|inflation|pce|ppi|payroll|jobs report|unemployment|gdp|jobless)\b", s):
        return True
    if re.search(r"\bfed\b|fomc|interest rate|bps", s):
        return True
    return n_in_event >= 4

def cmd_list(tags):
    seen = set()
    for tag in tags or DEFAULT_TAGS:
        events = get(f"/events?tag_slug={tag}&active=true&closed=false&limit=25&order=volume24hr&ascending=false")
        for e in events:
            for m in e.get("markets", []):
                if m["id"] in seen or m.get("closed") or not m.get("active"):
                    continue
                seen.add(m["id"])
                liq = float(m.get("liquidity") or 0)
                end = m.get("endDate", "")[:10]
                days = (datetime.date.fromisoformat(end) - datetime.date.today()).days if end else 0
                if liq < MIN_LIQUIDITY or days < MIN_DAYS:
                    continue
                print(f"{m['id']:>9}  ends {end}  liq ${liq/1000:>6.0f}k  "
                      f"[{e['title'][:40]}] {m['question']}")

def cmd_show(mid):
    m = market(mid)
    print(f"{m['id']}: {m['question']}\nends {m.get('endDate')}  closed={m.get('closed')}"
          f"  liquidity ${float(m.get('liquidity') or 0):,.0f}\nresolution source: {m.get('resolutionSource') or 'n/a'}\n")
    print(m.get("description", ""))

def cmd_record(mid, prob, reason):
    p = float(prob)
    if not 0 < p < 1:
        sys.exit("probability must be between 0 and 1, exclusive")
    rows = load()
    if any(r["market_id"] == mid for r in rows):
        sys.exit(f"market {mid} is already in the log; one forecast per market")
    m = market(mid)
    if m.get("closed"):
        sys.exit(f"market {mid} is closed")
    rows.append(dict(logged_utc=now(), market_id=mid, question=m["question"], end_date=m.get("endDate", "")[:10],
                     our_p=f"{p:.3f}", market_p=f"{yes_price(m):.3f}", reason=reason, outcome="", resolved_utc=""))
    save(rows)
    print(f"logged {mid}: ours {p:.3f} (market price stored, not shown)")

def cmd_score():
    rows = load()
    newly = 0
    for r in rows:
        if r["outcome"] == "":
            o = resolved(market(r["market_id"]))
            if o is not None:
                r["outcome"], r["resolved_utc"] = str(o), now()
                newly += 1
    save(rows)
    done = [r for r in rows if r["outcome"] != ""]
    print(f"{len(rows)} forecasts logged, {len(done)} resolved ({newly} newly), {len(rows) - len(done)} open")
    if not done:
        return
    brier = lambda key: sum((float(r[key]) - int(r["outcome"])) ** 2 for r in done) / len(done)
    ours, mkt = brier("our_p"), brier("market_p")
    wins = sum((float(r["our_p"]) - int(r["outcome"])) ** 2 < (float(r["market_p"]) - int(r["outcome"])) ** 2 for r in done)
    print(f"Brier (lower is better): ours {ours:.4f}  market {mkt:.4f}  -> "
          f"{'we beat the market' if ours < mkt else 'the market beat us' if mkt < ours else 'tie'}")
    print(f"Closer than the market on {wins} of {len(done)} resolved forecasts")
    for r in done[-10:]:
        print(f"  {r['end_date']}  {'YES' if r['outcome'] == '1' else 'NO ':3}  ours {r['our_p']}  mkt {r['market_p']}  {r['question'][:70]}")

def cmd_mech():
    rows = load(MECH_LOG)
    have = {r["market_id"] for r in rows}
    today, added, seen = datetime.date.today(), 0, set()
    for tag in MECH_TAGS:
        for e in get(f"/events?tag_slug={tag}&active=true&closed=false&limit=50&order=volume24hr&ascending=false"):
            ms = e.get("markets", [])
            for m in ms:
                if m["id"] in seen or m["id"] in have or m.get("closed") or not m.get("active"):
                    continue
                seen.add(m["id"])
                end = m.get("endDate", "")[:10]
                if not end or not MECH_DAYS[0] <= (datetime.date.fromisoformat(end) - today).days <= MECH_DAYS[1]:
                    continue
                if json.loads(m.get("outcomes") or "[]")[:2] != ["Yes", "No"] or not fixed_date(m["question"], e.get("title", ""), len(ms)):
                    continue
                ask, mid = m.get("bestAsk"), yes_price(m)
                if ask is None or not MECH_BAND[0] <= float(ask) <= MECH_BAND[1]:
                    continue
                rows.append(dict(logged_utc=now(), market_id=m["id"], question=m["question"], end_date=end,
                                 entry_ask=f"{float(ask):.3f}", mid=f"{mid:.3f}", outcome="", resolved_utc=""))
                added += 1
                print(f"paper-bought YES {m['id']} at {float(ask):.3f}, ends {end}: {m['question']}")
    save(rows, MECH_LOG, MECH_FIELDS)
    print(f"mechanical track: {added} new paper bets today, {len(rows)} total")

def mech_score():
    rows = load(MECH_LOG)
    if not rows:
        print("mechanical track: no paper bets yet")
        return
    for r in rows:
        if r["outcome"] == "":
            o = resolved(market(r["market_id"]))
            if o is not None:
                r["outcome"], r["resolved_utc"] = str(o), now()
    save(rows, MECH_LOG, MECH_FIELDS)
    done = [r for r in rows if r["outcome"] != ""]
    print(f"\nMechanical track (paper $1 per bet at the ask, before fees): {len(rows)} bets, {len(done)} resolved")
    if done:
        pnl = sum(int(r["outcome"]) / float(r["entry_ask"]) - 1 for r in done)
        wins = sum(r["outcome"] == "1" for r in done)
        print(f"Won {wins} of {len(done)}; profit ${pnl:+.2f} on ${len(done)} staked ({pnl / len(done) * 100:+.1f}% per bet)")

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "list":
        cmd_list(a[1:])
    elif a[0] == "show" and len(a) == 2:
        cmd_show(a[1])
    elif a[0] == "record" and len(a) == 4:
        cmd_record(a[1], a[2], a[3])
    elif a[0] == "score" and len(a) == 1:
        cmd_score()
        mech_score()
    elif a[0] == "mech" and len(a) == 1:
        cmd_mech()
    else:
        sys.exit(__doc__)
