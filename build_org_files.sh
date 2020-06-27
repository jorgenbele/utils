#!/bin/sh
# Author: Jørgen Bele Reinfjell
# Date: 10.04.2020 [dd.mm.yyyy]
# Description:
#   Utility to rebuild outdated markdown files
#   from emacs org-mode .org files. It recursively
#   builds all .org files it finds and stores the
#   sha1sum of the file to compare with later.
#   Requires kv.sh as kv
build_orgfiles() {
    local r=0
    for infile in *.org; do
        if [ "$infile" == "*.org" ]; then
            return
        fi
        ofile="${infile:0:((${#infile}-4))}.md"

        local key="$1/$infile"
        local curhash=`sha1sum "$infile"`
        local oldhash=`kv get "$key"`

        if ! [ "$oldhash" = "$curhash" ] && [ -f "$ofile" ]; then
            echo "$1/$infile: building $1/$ofile"
            # pandoc -o "$ofile" "$infile"
            emacs "$infile" --batch -f org-md-export-to-markdown --kill
            kv set "${key}" "$curhash"
            r=1
        else
            echo "$1/$infile: SKIPPING"
        fi
    done
    return "$r" # 1=built, 0=nothing was built
}

recursive_build() {
    local r=0
    for f in *; do
        if [ -d "$f" ]; then
            cd "$f"
            build_orgfiles "$1/$f" || r=1
            recursive_build "$1/$f" || r=1
            cd ..
        fi
    done
    return "$r"
}

export KV_FILE="$PWD/.kv"
kv init > /dev/null
recursive_build "$PWD" && echo "no changes detected"
