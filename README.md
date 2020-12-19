# golfgenius
Package to interface with Golf Genius

## parser.GGParser
- Parses golf genius data

## stats.Stats
- Computes statistics using golf genius data

## Install
```shell script
python setup.py install
```

## Example Usage

This exports all results to a directory

```python
from golfgenius.parser import GGParser

parser = GGParser(headless=True)
ggid = "A Golf Genius GGID Code"

try:
    for round_name, result in parser.iter_rounds(ggid):
        print(round_name, result)
finally:
    parser.close()

```
