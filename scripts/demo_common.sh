#!/bin/bash
# Узел, наблюдатель и плеер находятся в одном изолированном контейнере.
set -euo pipefail
kind="$1"; shift
if [ "$#" -lt 1 ]; then echo "Использование: demo_${kind}.sh /absolute/path/to/bag [скорость] [интервал_с] [смещение_с]" >&2; exit 2; fi
bag="$(cd "$1" && pwd)";rate="${2:-0.2}";span="${3:-1.2}";offset="${4:-0}"
here="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$PWD/demo_results"
result="$(mktemp -d "$PWD/demo_results/${kind}.XXXXXX")"
echo "Результат демонстрации: $result; скорость: ${rate}x; данные только для чтения"
docker run --rm --platform linux/amd64 --network none --shm-size=256m -e ROS_DOMAIN_ID=196 -e PYTHONDONTWRITEBYTECODE=1 -v "$bag":/bags/input:ro -v "$here":/demo:ro -v "$result":/results:rw "${RU_IMAGE:-lidar-near:v5-query-first-ru}" python3 /demo/demo_monitor.py /bags/input --rate "$rate" --span "$span" --offset "$offset" --output /results
