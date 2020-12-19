# golfgenius
Package to interface with Golf Genius. Currently
this uses screen scraping since an API key for the
Zogby group is not yet available. Therefore, it is
expected for there to be issues with stability until
this package is updated to fetch data from the golfgenius REST API.

## Install
You shouldn't have to install this package directly, instead it will
be installed automatically by [power_rankings](https://github.com/cswelton/power_rankings)


## parser.GGParser
- Parses golf genius data

## stats.Stats
- Computes statistics using golf genius data

## Example Usage

This exports all results to a directory

```
from golfgenius.parser import GGParser

parser = GGParser(headless=True)
ggid = "A Golf Genius GGID Code"

try:
    for round_name, result in parser.iter_rounds(ggid):
        print(round_name, result)
finally:
    parser.close()

```
