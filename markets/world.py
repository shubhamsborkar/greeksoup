"""Every country as a home market, from Yahoo's free feed.

India and the United States have a file of their own (a results calendar, the
exchange's filings, the market's own macro cards). Every other country comes
from the table here: its currency, the exchanges Yahoo's feed carries with the
suffix each one takes, the regular session in the exchange's own time zone, and
the index Risk measures against. A country whose exchange the feed does not
carry still gets its currency and the world index, so a reader anywhere picks
their own country and the home screens take its shape.

A row that is wrong or missing is a one-line fix in this table; the Settings
screen's feedback door is where a reader says so.
"""
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python 3.8
    ZoneInfo = None

WORLD_BENCH, WORLD_BENCH_LABEL = "ACWI", "MSCI ACWI"     # the world index, through the ACWI fund

# id: (label, currency, exchanges, session, benchmark, benchmark_label)
#   exchanges  [(name, yahoo_suffix), ...]   the first is the default; [] when the feed has none
#   session    (time zone, "HH:MM", "HH:MM", days)   days "mf" Monday to Friday, "sut" Sunday to Thursday
#   benchmark  Yahoo symbol of the index Risk measures against; None means the world index
EXCHANGES = {
    "ar": ("Argentina", "ARS", [("BCBA", ".BA")], ("America/Argentina/Buenos_Aires", "11:00", "17:00", "mf"), "^MERV", "S&P Merval"),
    "au": ("Australia", "AUD", [("ASX", ".AX")], ("Australia/Sydney", "10:00", "16:00", "mf"), "^AXJO", "S&P/ASX 200"),
    "at": ("Austria", "EUR", [("VIE", ".VI")], ("Europe/Vienna", "09:00", "17:30", "mf"), "^ATX", "ATX"),
    "be": ("Belgium", "EUR", [("BRU", ".BR")], ("Europe/Brussels", "09:00", "17:30", "mf"), "^BFX", "BEL 20"),
    "br": ("Brazil", "BRL", [("B3", ".SA")], ("America/Sao_Paulo", "10:00", "17:00", "mf"), "^BVSP", "Ibovespa"),
    "ca": ("Canada", "CAD", [("TSX", ".TO"), ("TSXV", ".V")], ("America/Toronto", "09:30", "16:00", "mf"), "^GSPTSE", "S&P/TSX Composite"),
    "cl": ("Chile", "CLP", [("SSE", ".SN")], ("America/Santiago", "09:30", "16:00", "mf"), "^IPSA", "S&P IPSA"),
    "cn": ("China", "CNY", [("SSE", ".SS"), ("SZSE", ".SZ")], ("Asia/Shanghai", "09:30", "15:00", "mf"), "000001.SS", "SSE Composite"),
    "co": ("Colombia", "COP", [("BVC", ".CL")], ("America/Bogota", "09:30", "16:00", "mf"), None, None),
    "cz": ("Czech Republic", "CZK", [("PSE", ".PR")], ("Europe/Prague", "09:00", "16:20", "mf"), None, None),
    "dk": ("Denmark", "DKK", [("CPH", ".CO")], ("Europe/Copenhagen", "09:00", "17:00", "mf"), "^OMXC25", "OMX Copenhagen 25"),
    "eg": ("Egypt", "EGP", [("EGX", ".CA")], ("Africa/Cairo", "10:00", "14:30", "sut"), "^CASE30", "EGX 30"),
    "ee": ("Estonia", "EUR", [("TAL", ".TL")], ("Europe/Tallinn", "10:00", "16:00", "mf"), None, None),
    "fi": ("Finland", "EUR", [("HEL", ".HE")], ("Europe/Helsinki", "10:00", "18:30", "mf"), "^OMXH25", "OMX Helsinki 25"),
    "fr": ("France", "EUR", [("PAR", ".PA")], ("Europe/Paris", "09:00", "17:30", "mf"), "^FCHI", "CAC 40"),
    "de": ("Germany", "EUR", [("XETRA", ".DE"), ("FRA", ".F")], ("Europe/Berlin", "09:00", "17:30", "mf"), "^GDAXI", "DAX"),
    "gr": ("Greece", "EUR", [("ATH", ".AT")], ("Europe/Athens", "10:30", "17:20", "mf"), "GD.AT", "Athens General"),
    "hk": ("Hong Kong", "HKD", [("HKEX", ".HK")], ("Asia/Hong_Kong", "09:30", "16:00", "mf"), "^HSI", "Hang Seng"),
    "hu": ("Hungary", "HUF", [("BUD", ".BD")], ("Europe/Budapest", "09:00", "17:00", "mf"), None, None),
    "is": ("Iceland", "ISK", [("ICE", ".IC")], ("Atlantic/Reykjavik", "09:30", "15:30", "mf"), None, None),
    "id": ("Indonesia", "IDR", [("IDX", ".JK")], ("Asia/Jakarta", "09:00", "16:00", "mf"), "^JKSE", "IDX Composite"),
    "ie": ("Ireland", "EUR", [("ISE", ".IR")], ("Europe/Dublin", "08:00", "16:30", "mf"), "^ISEQ", "ISEQ All-Share"),
    "il": ("Israel", "ILS", [("TASE", ".TA")], ("Asia/Jerusalem", "10:00", "17:15", "sut"), "^TA125.TA", "TA-125"),
    "it": ("Italy", "EUR", [("MIL", ".MI")], ("Europe/Rome", "09:00", "17:30", "mf"), "FTSEMIB.MI", "FTSE MIB"),
    "jp": ("Japan", "JPY", [("TSE", ".T")], ("Asia/Tokyo", "09:00", "15:30", "mf"), "^N225", "Nikkei 225"),
    "kr": ("South Korea", "KRW", [("KRX", ".KS"), ("KOSDAQ", ".KQ")], ("Asia/Seoul", "09:00", "15:30", "mf"), "^KS11", "KOSPI"),
    "kw": ("Kuwait", "KWD", [("BK", ".KW")], ("Asia/Kuwait", "09:00", "12:40", "sut"), None, None),
    "lv": ("Latvia", "EUR", [("RSE", ".RG")], ("Europe/Riga", "10:00", "16:00", "mf"), None, None),
    "lt": ("Lithuania", "EUR", [("VSE", ".VS")], ("Europe/Vilnius", "10:00", "16:00", "mf"), None, None),
    "my": ("Malaysia", "MYR", [("KLSE", ".KL")], ("Asia/Kuala_Lumpur", "09:00", "17:00", "mf"), "^KLSE", "FTSE Bursa Malaysia KLCI"),
    "mx": ("Mexico", "MXN", [("BMV", ".MX")], ("America/Mexico_City", "08:30", "15:00", "mf"), "^MXX", "S&P/BMV IPC"),
    "nl": ("Netherlands", "EUR", [("AMS", ".AS")], ("Europe/Amsterdam", "09:00", "17:30", "mf"), "^AEX", "AEX"),
    "nz": ("New Zealand", "NZD", [("NZX", ".NZ")], ("Pacific/Auckland", "10:00", "16:45", "mf"), "^NZ50", "S&P/NZX 50"),
    "no": ("Norway", "NOK", [("OSL", ".OL")], ("Europe/Oslo", "09:00", "16:20", "mf"), "OSEBX.OL", "OSEBX"),
    "pe": ("Peru", "PEN", [("BVL", ".LM")], ("America/Lima", "09:00", "16:00", "mf"), None, None),
    "ph": ("Philippines", "PHP", [("PSE", ".PS")], ("Asia/Manila", "09:30", "15:00", "mf"), "PSEI.PS", "PSEi"),
    "pl": ("Poland", "PLN", [("WSE", ".WA")], ("Europe/Warsaw", "09:00", "17:00", "mf"), None, None),
    "pt": ("Portugal", "EUR", [("LIS", ".LS")], ("Europe/Lisbon", "08:00", "16:30", "mf"), "PSI20.LS", "PSI"),
    "qa": ("Qatar", "QAR", [("QSE", ".QA")], ("Asia/Qatar", "09:30", "13:15", "sut"), None, None),
    "ru": ("Russia", "RUB", [("MOEX", ".ME")], ("Europe/Moscow", "10:00", "18:40", "mf"), None, None),
    "sa": ("Saudi Arabia", "SAR", [("TADAWUL", ".SR")], ("Asia/Riyadh", "10:00", "15:00", "sut"), "^TASI.SR", "TASI"),
    "sg": ("Singapore", "SGD", [("SGX", ".SI")], ("Asia/Singapore", "09:00", "17:00", "mf"), "^STI", "Straits Times"),
    "za": ("South Africa", "ZAR", [("JSE", ".JO")], ("Africa/Johannesburg", "09:00", "17:00", "mf"), "^J203.JO", "FTSE/JSE All Share"),
    "es": ("Spain", "EUR", [("BME", ".MC")], ("Europe/Madrid", "09:00", "17:30", "mf"), "^IBEX", "IBEX 35"),
    "lk": ("Sri Lanka", "LKR", [("CSE", ".CM")], ("Asia/Colombo", "09:30", "14:30", "mf"), None, None),
    "se": ("Sweden", "SEK", [("STO", ".ST")], ("Europe/Stockholm", "09:00", "17:30", "mf"), "^OMX", "OMX Stockholm 30"),
    "ch": ("Switzerland", "CHF", [("SIX", ".SW")], ("Europe/Zurich", "09:00", "17:30", "mf"), "^SSMI", "SMI"),
    "tw": ("Taiwan", "TWD", [("TWSE", ".TW"), ("TPEx", ".TWO")], ("Asia/Taipei", "09:00", "13:30", "mf"), "^TWII", "TAIEX"),
    "th": ("Thailand", "THB", [("SET", ".BK")], ("Asia/Bangkok", "10:00", "16:30", "mf"), "^SET.BK", "SET"),
    "tr": ("Turkey", "TRY", [("BIST", ".IS")], ("Europe/Istanbul", "10:00", "18:00", "mf"), "XU100.IS", "BIST 100"),
    "ae": ("United Arab Emirates", "AED", [("DFM", ".AE"), ("ADX", ".AD")], ("Asia/Dubai", "10:00", "15:00", "mf"), None, None),
    "gb": ("United Kingdom", "GBP", [("LSE", ".L")], ("Europe/London", "08:00", "16:30", "mf"), "^FTSE", "FTSE 100"),
    "vn": ("Vietnam", "VND", [("HOSE", ".VN")], ("Asia/Ho_Chi_Minh", "09:00", "14:45", "mf"), None, None),
}

# Every other country: label and currency. No exchange on the feed, so the
# session dot stays off and Risk measures against the world index.
COUNTRIES = {
    "af": ("Afghanistan", "AFN"), "al": ("Albania", "ALL"), "dz": ("Algeria", "DZD"), "ad": ("Andorra", "EUR"),
    "ao": ("Angola", "AOA"), "ag": ("Antigua and Barbuda", "XCD"), "am": ("Armenia", "AMD"), "az": ("Azerbaijan", "AZN"),
    "bs": ("Bahamas", "BSD"), "bh": ("Bahrain", "BHD"), "bd": ("Bangladesh", "BDT"), "bb": ("Barbados", "BBD"),
    "by": ("Belarus", "BYN"), "bz": ("Belize", "BZD"), "bj": ("Benin", "XOF"), "bt": ("Bhutan", "BTN"),
    "bo": ("Bolivia", "BOB"), "ba": ("Bosnia and Herzegovina", "BAM"), "bw": ("Botswana", "BWP"), "bn": ("Brunei", "BND"),
    "bg": ("Bulgaria", "BGN"), "bf": ("Burkina Faso", "XOF"), "bi": ("Burundi", "BIF"), "kh": ("Cambodia", "KHR"),
    "cm": ("Cameroon", "XAF"), "cv": ("Cape Verde", "CVE"), "cf": ("Central African Republic", "XAF"), "td": ("Chad", "XAF"),
    "km": ("Comoros", "KMF"), "cg": ("Congo", "XAF"), "cd": ("Congo, Democratic Republic", "CDF"), "cr": ("Costa Rica", "CRC"),
    "ci": ("Côte d'Ivoire", "XOF"), "hr": ("Croatia", "EUR"), "cu": ("Cuba", "CUP"), "cy": ("Cyprus", "EUR"),
    "dj": ("Djibouti", "DJF"), "dm": ("Dominica", "XCD"), "do": ("Dominican Republic", "DOP"), "ec": ("Ecuador", "USD"),
    "sv": ("El Salvador", "USD"), "gq": ("Equatorial Guinea", "XAF"), "er": ("Eritrea", "ERN"), "sz": ("Eswatini", "SZL"),
    "et": ("Ethiopia", "ETB"), "fj": ("Fiji", "FJD"), "ga": ("Gabon", "XAF"), "gm": ("Gambia", "GMD"),
    "ge": ("Georgia", "GEL"), "gh": ("Ghana", "GHS"), "gd": ("Grenada", "XCD"), "gt": ("Guatemala", "GTQ"),
    "gn": ("Guinea", "GNF"), "gw": ("Guinea-Bissau", "XOF"), "gy": ("Guyana", "GYD"), "ht": ("Haiti", "HTG"),
    "hn": ("Honduras", "HNL"), "ir": ("Iran", "IRR"), "iq": ("Iraq", "IQD"), "jm": ("Jamaica", "JMD"),
    "jo": ("Jordan", "JOD"), "kz": ("Kazakhstan", "KZT"), "ke": ("Kenya", "KES"), "ki": ("Kiribati", "AUD"),
    "kp": ("North Korea", "KPW"), "xk": ("Kosovo", "EUR"), "kg": ("Kyrgyzstan", "KGS"), "la": ("Laos", "LAK"),
    "lb": ("Lebanon", "LBP"), "ls": ("Lesotho", "LSL"), "lr": ("Liberia", "LRD"), "ly": ("Libya", "LYD"),
    "li": ("Liechtenstein", "CHF"), "lu": ("Luxembourg", "EUR"), "mg": ("Madagascar", "MGA"), "mw": ("Malawi", "MWK"),
    "mv": ("Maldives", "MVR"), "ml": ("Mali", "XOF"), "mt": ("Malta", "EUR"), "mh": ("Marshall Islands", "USD"),
    "mr": ("Mauritania", "MRU"), "mu": ("Mauritius", "MUR"), "fm": ("Micronesia", "USD"), "md": ("Moldova", "MDL"),
    "mc": ("Monaco", "EUR"), "mn": ("Mongolia", "MNT"), "me": ("Montenegro", "EUR"), "ma": ("Morocco", "MAD"),
    "mz": ("Mozambique", "MZN"), "mm": ("Myanmar", "MMK"), "na": ("Namibia", "NAD"), "nr": ("Nauru", "AUD"),
    "np": ("Nepal", "NPR"), "ni": ("Nicaragua", "NIO"), "ne": ("Niger", "XOF"), "ng": ("Nigeria", "NGN"),
    "mk": ("North Macedonia", "MKD"), "om": ("Oman", "OMR"), "pk": ("Pakistan", "PKR"), "pw": ("Palau", "USD"),
    "ps": ("Palestine", "ILS"), "pa": ("Panama", "USD"), "pg": ("Papua New Guinea", "PGK"), "py": ("Paraguay", "PYG"),
    "ro": ("Romania", "RON"), "rw": ("Rwanda", "RWF"), "kn": ("Saint Kitts and Nevis", "XCD"), "lc": ("Saint Lucia", "XCD"),
    "vc": ("Saint Vincent and the Grenadines", "XCD"), "ws": ("Samoa", "WST"), "sm": ("San Marino", "EUR"),
    "st": ("São Tomé and Príncipe", "STN"), "sn": ("Senegal", "XOF"), "rs": ("Serbia", "RSD"), "sc": ("Seychelles", "SCR"),
    "sl": ("Sierra Leone", "SLE"), "sk": ("Slovakia", "EUR"), "si": ("Slovenia", "EUR"), "sb": ("Solomon Islands", "SBD"),
    "so": ("Somalia", "SOS"), "ss": ("South Sudan", "SSP"), "sd": ("Sudan", "SDG"), "sr": ("Suriname", "SRD"),
    "sy": ("Syria", "SYP"), "tj": ("Tajikistan", "TJS"), "tz": ("Tanzania", "TZS"), "tl": ("Timor-Leste", "USD"),
    "tg": ("Togo", "XOF"), "to": ("Tonga", "TOP"), "tt": ("Trinidad and Tobago", "TTD"), "tn": ("Tunisia", "TND"),
    "tm": ("Turkmenistan", "TMT"), "tv": ("Tuvalu", "AUD"), "ug": ("Uganda", "UGX"), "ua": ("Ukraine", "UAH"),
    "uy": ("Uruguay", "UYU"), "uz": ("Uzbekistan", "UZS"), "vu": ("Vanuatu", "VUV"), "va": ("Vatican City", "EUR"),
    "ve": ("Venezuela", "VES"), "ye": ("Yemen", "YER"), "zm": ("Zambia", "ZMW"), "zw": ("Zimbabwe", "ZWG"),
}

SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥", "KRW": "₩", "INR": "₹", "ILS": "₪",
           "TRY": "₺", "NGN": "₦", "PHP": "₱", "VND": "₫", "THB": "฿", "UAH": "₴", "KZT": "₸", "PYG": "₲",
           "BRL": "R$", "CAD": "C$", "AUD": "A$", "NZD": "NZ$", "HKD": "HK$", "SGD": "S$", "TWD": "NT$",
           "MXN": "MX$", "ZAR": "R", "CHF": "CHF ", "RUB": "₽", "PLN": "zł", "CRC": "₡", "GHS": "₵", "LAK": "₭",
           "MNT": "₮", "AZN": "₼", "GEL": "₾"}


class Market:
    """A market built from one table row; the same face as markets/us.py."""

    def __init__(self, rid):
        if rid in EXCHANGES:
            label, cur, exchanges, session, bench, bench_label = EXCHANGES[rid]
        else:
            label, cur = COUNTRIES[rid]
            exchanges, session, bench, bench_label = [], None, None, None
        self._suffix = {name: suf for name, suf in exchanges}
        self._session = session
        self.META = {
            "id": rid, "label": label,
            "currency": cur, "symbol": SYMBOLS.get(cur, cur + " "), "locale": f"en-{rid.upper()}",
            "exchanges": [name for name, _ in exchanges],
            "session_label": exchanges[0][0] if exchanges else "",
            "benchmark": bench or WORLD_BENCH, "benchmark_label": bench_label or WORLD_BENCH_LABEL,
            "econ_country": rid.upper(),
            "filings": "", "units": "",
            "record": "quotes" if exchanges else "currency",
        }

    def is_open(self, now=None):
        """The regular session in the exchange's own time zone; never open
        without an exchange on the feed."""
        if not self._session or ZoneInfo is None:
            return False
        tz, o, c, days = self._session
        now = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo(tz))
        if now.weekday() in ((5, 6) if days == "mf" else (4, 5)):
            return False
        hm = now.hour * 60 + now.minute
        oh, om = map(int, o.split(":"))
        ch, cm = map(int, c.split(":"))
        return oh * 60 + om <= hm < ch * 60 + cm

    def ysym(self, symbol, exch=None):
        """RR on LSE -> RR.L; a symbol that already carries a suffix is returned as it is."""
        s = (symbol or "").upper()
        if not s or "." in s or not self._suffix:
            return s
        first = self.META["exchanges"][0]
        return s + self._suffix.get((exch or first).upper(), self._suffix[first])

    def from_ysym(self, ysym):
        """RR.L -> ("RR", "LSE"); None when the suffix is not this market's."""
        s = (ysym or "").upper()
        for exch, suf in (self._suffix or {}).items():
            if suf and s.endswith(suf) and len(s) > len(suf):
                return s[:-len(suf)], exch
        return None


def ids():
    return sorted(set(EXCHANGES) | set(COUNTRIES))
