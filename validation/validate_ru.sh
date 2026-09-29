#!/bin/bash
# Автономная проверка. Все эталоны читаются только из соседних архивов.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
image="${RU_IMAGE:-lidar-near:v5-query-first-ru}"
work="${1:-$PWD/ru_validation_run}"
if [ -e "$work" ]; then echo 'Каталог результата уже существует. Укажите новый путь.' >&2; exit 2; fi
mkdir -p "$work"
work="$(cd "$work" && pwd)"
python3 "$here/tools/unpack.py" "$here" "$work"
args=(--rm --platform linux/amd64 --network none --shm-size=256m -e PYTHONDONTWRITEBYTECODE=1 -e QUERY_INSTALLED=1 -e ROS_DOMAIN_ID=198 -e DIRECT_ARTIFACTS=/results -v "$work/direct-validation":/workspace:ro -v "$here/tools":/ru-checks:ro -v "$here/solution":/ru-source:ro -v "$work/results":/results:rw)
docker run "${args[@]}" "$image" python3 /ru-checks/verify_localization.py /workspace/candidates/direct_query_first /ru-source /results/localization.json
docker run "${args[@]}" "$image" python3 /workspace/experiments/rescue_query_first/installed_audit.py /ru-source /results/installed.json
docker run "${args[@]}" "$image" python3 /workspace/experiments/rescue_query_first/focused.py
docker run "${args[@]}" "$image" python3 /ru-checks/parity_ru.py
docker run "${args[@]}" "$image" python3 /workspace/experiments/rescue_query_first/baseline_checks.py selected_parity
docker run "${args[@]}" "$image" python3 /workspace/experiments/rescue_query_first/baseline_checks.py tests
docker run "${args[@]}" "$image" python3 /workspace/experiments/rescue_query_first/baseline_checks.py far_regression_v3 /results/far.json
docker run "${args[@]}" "$image" python3 /workspace/experiments/rescue_query_first/ros_e10_smoke.py /results/ros_e10.json /opt/detector/install/foreign_object_detector/lib/python3.10/site-packages/foreign_object_detector/config/production.yaml
echo 'ПРОВЕРКА ПРОЙДЕНА. Результаты:' "$work/results"
