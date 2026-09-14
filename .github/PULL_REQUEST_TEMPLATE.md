## What this changes

One or two sentences.

## Which contract it follows

- [ ] A broker file (`brokers/README.md`)
- [ ] A market file (`markets/README.md`)
- [ ] A data provider file (`data_providers/CONTRACT.md`)
- [ ] The desk itself (say which screen or source)

## What stays true

- [ ] It places no orders and adds no order path.
- [ ] Keys are read from the environment only and written nowhere else.
- [ ] Anything the reader sees is in plain words; engineering detail is in `TECHNICAL.md` or a contract.
- [ ] `python -m pytest tests -q` passes.
- [ ] If what ships changed: a line at the top of `VERSION` and `python scripts/make_manifest.py` run.

## How you tested it

Which broker, market or provider, on which computer, and what you saw.
