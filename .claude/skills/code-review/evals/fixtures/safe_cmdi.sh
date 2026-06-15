#!/bin/bash
set -euo pipefail
archive="$1"
dest="$2"
tar -xf "$archive" -C "$dest" --   # no eval, quoted, -- ends option parsing
