#!/bin/sh
# date: 10.04.2020 
# description:
# kv is a key-value store using
# a locally backed file

if [ -z "$KEY_CHARS" ]; then
    KEY_CHARS="[A-Za-z0-9_/]"
fi

kv_file="$KV_FILE"
if [ -z "$KV_FILE" ]; then
    kv_file=".kv"
fi

kv_is_valid_key() {
    local key="$2"
    grep "^${KEY_CHARS}${KEY_CHARS}*" <<EOL
$2
EOL
}

kv_init() {
    if [ -f "$kv_file" ]; then
        echo "$kv_file already exists, not initiating"
        return 1
    fi
    touch "$kv_file"
    return 0
}

kv_get() {
    local key="$2"
    local old_ifs="$IFS"
    IFS="="
    for x in `grep -m 1 "^${key}=" < "$kv_file" | sed 's/^.*=//g'`; do
        echo "$x"
        IFS="$old_ifs"
        return 0
    done
    IFS="$old_ifs"
    return 1
}

kv_has() {
    kv_get "$@" > /dev/null
}

kv_set() {
    local key="$2"
    local value="$3"

    if ! kv_has "$@"; then
        echo "${key}=${value}" >> "$kv_file"
        return 0
    fi
    sed -i "s~^${key}=.*~${key}=${value}~g" "$kv_file"
}

kv_keys() {
    sed "s/=.*$//g" < "$kv_file"
}

kv_values() {
    sed "s/^.*=//g" < "$kv_file"
}

kv_help() {
    echo "usage: "$1" (init | has <key> | get <key> | set <key> <val> | keys | values | is_valid_key <key_candidate>)"
}

kv() {
    local r
    r=0
    case "$1" in
        init)         kv_init "$@"   ; r="$?" ;;
        has)          kv_has "$@"    ; r="$?" ;;
        get)          kv_get "$@"    ; r="$?" ;;
        set)          kv_set "$@"    ; r="$?" ;;
        keys)         kv_keys "$@"   ; r="$?" ;;
        values)       kv_values "$@" ; r="$?" ;;
        is_valid_key) kv_is_valid_key "$@" ; r="$?" ;;
        help|-h|--help) kv_help "$@" ;; 
        .*) 
            echo "$1" is not a valid command
            kv_help "$@"
            r=1
            ;;
        *) kv_help "$@" ;; 
    esac
    return "$r"
}

case $- in
    *i*) ;;
    *) kv "$@" ;;
esac
