"""Your reports on Tell us carries the whole reply, so the page can show its opening and
open the rest with Read more. It used to keep the first 600 characters, which cut a long
reply before it said what to do (issue #5's reply stopped mid-sentence)."""
import support


class _Resp:
    def __init__(self, data):
        self.status_code, self._data = 200, data

    def json(self):
        return self._data


def _github(body):
    def get(url, **kw):
        if url.endswith("/comments?per_page=1&sort=created&direction=desc"):
            return _Resp([{"user": {"login": "shubhamsborkar"}, "created_at": "2026-09-28T03:55:10Z", "body": body}])
        return _Resp({"state": "open", "comments": 1, "html_url": "https://github.com/shubhamsborkar/greeksoup/issues/5"})
    return get


def test_a_long_reply_comes_back_whole(monkeypatch):
    body = "Thank you for sending this.\n\n" + "A sentence about the fix. " * 60 + "\n\nUpdate from the strip."
    monkeypatch.setattr(support, "_cache", {})
    monkeypatch.setattr(support.requests, "get", _github(body))
    last = support._fetch(5)["last"]
    assert last["text"] == body and last["cut"] is False
    assert last["who"] == "shubhamsborkar" and last["at"] == "2026-09-28"


def test_a_runaway_reply_is_capped_and_says_so(monkeypatch):
    body = "x" * (support.REPLY_MAX + 10)
    monkeypatch.setattr(support, "_cache", {})
    monkeypatch.setattr(support.requests, "get", _github(body))
    last = support._fetch(6)["last"]
    assert len(last["text"]) == support.REPLY_MAX and last["cut"] is True
