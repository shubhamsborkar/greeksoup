"""The economic calendar from the public record, with no key and no Yahoo.

Three readers, each one page, each keyless, used when the free feed's own calendar
endpoint refuses the address (it answers 429 for days at a time while quotes and
charts still answer):

  - Forex Factory's weekly calendar (nfs.faireconomy.media): this week, the nine
    major currencies, with impact, forecast and previous. The week runs Sunday to
    Saturday and the file is the current week only.
  - The BLS release schedule (bls.gov/schedule): every US Bureau of Labor Statistics
    print, this month and the next two, with the period and the time in Eastern.
  - The Fed's FOMC calendar (federalreserve.gov): every meeting of the year; the
    statement lands at 14:00 Eastern on the second day.

Rows come back in the desk's calendar shape: date and time in UTC, a two-letter
country, the event, an impact, estimate, previous, actual. Nothing here is a view;
it is a list of dates the record already publishes.
"""

import html
import json
import re
from datetime import date, datetime, timedelta

import requests

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) GreekSoup/1.0 (+https://greeksoup.ai)"}
FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
BLS_URL = "https://www.bls.gov/schedule/{y}/{m:02d}_sched.htm"
FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

FF_COUNTRY = {"USD": "US", "EUR": "EU", "GBP": "GB", "JPY": "JP", "CNY": "CN", "CAD": "CA",
              "AUD": "AU", "NZD": "NZ", "CHF": "CH"}
# the BLS prints that move markets; everything else on the schedule is Medium
BLS_HIGH = ("employment situation", "consumer price index", "producer price index",
            "job openings", "employment cost index", "real earnings")
MONTHS = {m: i for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July",
                                      "August", "September", "October", "November", "December"), 1)}


def _et_offset_hours(d):
    """Eastern time against UTC on a date: daylight time (UTC-4) from the second Sunday of
    March to the first Sunday of November, standard time (UTC-5) otherwise. A rule, so
    that a Windows install without a time-zone database still gets it right."""
    def nth_sunday(y, m, n):
        first = date(y, m, 1)
        off = (6 - first.weekday()) % 7
        return first + timedelta(days=off + 7 * (n - 1))
    return -4 if nth_sunday(d.year, 3, 2) <= d < nth_sunday(d.year, 11, 1) else -5


def _et_to_utc(d, hh, mm):
    dt = datetime(d.year, d.month, d.day, hh, mm) - timedelta(hours=_et_offset_hours(d))
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")


def _row(dte, tme, country, event, impact, estimate="", previous="", actual="", period=""):
    return {"date": dte, "time": tme, "country": country, "event": event, "impact": impact,
            "estimate": estimate or None, "previous": previous or None, "actual": actual or None,
            "period": period, "unit": ""}


def forex_factory():
    """This week's prints across the nine majors, from Forex Factory's public weekly file."""
    try:
        r = requests.get(FF_URL, headers=UA, timeout=20)
        if r.status_code != 200:
            return []
        rows = r.json()
    except (requests.RequestException, ValueError):
        return []
    out = []
    for x in rows if isinstance(rows, list) else []:
        c = FF_COUNTRY.get(str(x.get("country") or ""))
        imp = str(x.get("impact") or "")
        if not c or imp not in ("High", "Medium", "Low"):
            continue      # holidays and "All"-country notes stay out
        raw = str(x.get("date") or "")
        m = re.match(r"(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):\d{2}([+-]\d{2}):(\d{2})", raw)
        if not m:
            continue
        local = datetime.strptime(m.group(1) + m.group(2) + m.group(3), "%Y-%m-%d%H%M")
        off = timedelta(hours=int(m.group(4)), minutes=int(m.group(5)) * (1 if m.group(4).startswith("+") else -1))
        utc = local - off
        out.append(_row(utc.strftime("%Y-%m-%d"), utc.strftime("%H:%M"), c, str(x.get("title") or "").strip(), imp,
                        str(x.get("forecast") or "").strip(), str(x.get("previous") or "").strip()))
    return out


def bls_schedule(months=3):
    """Every BLS print this month and the next `months - 1`, from the Bureau's own schedule pages."""
    out, today = [], date.today()
    y, m = today.year, today.month
    for _ in range(months):
        try:
            r = requests.get(BLS_URL.format(y=y, m=m), headers=UA, timeout=20)
        except requests.RequestException:
            r = None
        if r is not None and r.status_code == 200:
            for mm, dd, cell in re.findall(r'<td id="d(\d\d)(\d\d)">(.*?)</td>', r.text, flags=re.S):
                if int(mm) != m:
                    continue      # the grid shows the neighbouring months' edge days too
                d = date(y, m, int(dd))
                for name, period, clock in re.findall(r"<strong>(.*?)<br></strong>(.*?)<br>(\d{1,2}:\d{2} [AP]M)</p>", cell, flags=re.S):
                    name = html.unescape(re.sub(r"<[^>]+>", "", name)).strip()
                    period = html.unescape(re.sub(r"<[^>]+>", "", period)).strip()
                    t = datetime.strptime(clock, "%I:%M %p")
                    dte, tme = _et_to_utc(d, t.hour, t.minute)
                    imp = "High" if any(k in name.lower() for k in BLS_HIGH) else "Medium"
                    out.append(_row(dte, tme, "US", name, imp, period=period))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def fomc_meetings():
    """Every FOMC meeting on the Fed's calendar page, as the statement time on the last day."""
    try:
        r = requests.get(FOMC_URL, headers=UA, timeout=20)
        if r.status_code != 200:
            return []
    except requests.RequestException:
        return []
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "|", r.text))
    out = []
    for year in re.findall(r"(\d{4}) FOMC Meetings", text):
        seg = text[text.find(f"{year} FOMC Meetings"):]
        nxt = re.search(r"\d{4} FOMC Meetings", seg[10:])
        if nxt:
            seg = seg[:nxt.start() + 10]
        for month, days in re.findall(r"\|\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s*\|+\s*\|?\s*(\d{1,2}(?:-\d{1,2})?)\*?\s*\|", seg):
            last = int(days.split("-")[-1])
            try:
                d = date(int(year), MONTHS[month], last)
            except ValueError:
                continue
            dte, tme = _et_to_utc(d, 14, 0)
            out.append(_row(dte, tme, "US", "FOMC rate decision and statement", "High"))
    return out


def calendar(days=60):
    """The three readers merged, today onward, `days` ahead, sorted. Duplicates across the
    readers (a BLS print that Forex Factory also lists this week) keep the Forex Factory
    row, which carries the forecast."""
    today = date.today().strftime("%Y-%m-%d")
    end = (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")
    ff = [r for r in forex_factory() if today <= r["date"] <= end]
    seen_days = {(r["date"], r["country"]) for r in ff}
    rest = []
    for r in bls_schedule() + fomc_meetings():
        if not (today <= r["date"] <= end):
            continue
        if (r["date"], r["country"]) in seen_days and r["impact"] != "High":
            continue      # Forex Factory already covers that day; keep only the big US prints from BLS as well
        rest.append(r)
    # a High BLS row on a day Forex Factory covers is a likely duplicate of a FF row on the same
    # theme; drop it when a FF row that day shares a word of the name
    def dup(r):
        words = {w for w in re.findall(r"[a-z]{4,}", r["event"].lower())} - {"index", "situation", "survey", "monthly"}
        for f in ff:
            if f["date"] == r["date"] and f["country"] == r["country"] and words & set(re.findall(r"[a-z]{4,}", f["event"].lower())):
                return True
        return False
    rows = ff + [r for r in rest if not dup(r)]
    rows.sort(key=lambda r: (r["date"], r["time"]))
    return rows


if __name__ == "__main__":
    rows = calendar()
    print(json.dumps(rows[:8], indent=1))
    print(len(rows), "rows")
