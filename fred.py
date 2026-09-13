"""FRED, keyless, one series at a time. FRED's CDN stalls python-requests' TLS
fingerprint but serves curl fine, so this shells out to curl for that one host.
Shared by the Macro screen and any market file that adds its own FRED rows."""

import subprocess


def csv(series):
    """[(YYYY-MM-DD, value)] ascending; [] on any failure."""
    try:
        r = subprocess.run(
            ["curl", "-s", "-m", "25",
             f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"],
            capture_output=True, text=True, timeout=30)
        lines = r.stdout.strip().splitlines()[1:]
        out = []
        for ln in lines:
            d, _, v = ln.partition(",")
            v = v.strip()
            if v and v != ".":
                try:
                    out.append((d, float(v)))
                except ValueError:
                    pass
        return out
    except Exception:  # noqa: BLE001
        return []
