#!/bin/sh
# dev loop: rebuild payload, install with the given extra args via the source CLI, rebuild matching symbols, run live_check
cd /f/project/oot-master-mod
python tools/make_release.py >/dev/null 2>&1 || { echo build failed; python tools/build_core.py --features hero_core --compat --base 0x4F87000 2>&1 | grep -E "error"; exit 1; }
taskkill //F //IM lichii.exe >/dev/null 2>&1
python app/ootconfig.py --cli --emu "E:/Switch2/Emu/Fritchii-v4.1-Windows-x64/Fritchii-v4.1" --preset 0 "$@" 2>&1 | grep installed
python tools/build_core.py --features hero_core --compat --base 0x4F87000 >/dev/null 2>&1
python tools/live_check.py --press "" --linger 1 > /tmp/lc.txt 2>&1
grep -n "txt\|Traceback" /tmp/lc.txt | cut -c1-260
taskkill //F //IM lichii.exe >/dev/null 2>&1
