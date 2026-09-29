#!/usr/bin/env python3
"""Проверка файлов поставки без ROS, Docker и внешних данных. Ничего не изменяет."""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    errors: list[str] = []
    required = [
        'README.md', 'Dockerfile', '.dockerignore',
        'docs/ARCHITECTURE.md', 'docs/ALGORITHM.md', 'docs/DEPLOYMENT.md',
        'docs/API.md', 'docs/RESULTS.md', 'docs/VALIDATION.md',
        'docs/results.json', 'tests/test_contract.py',
        'docs/README.md',
    ]
    for name in required:
        if not (ROOT / name).is_file():
            errors.append(f'Отсутствует: {name}')

    manifest = json.loads((ROOT / 'validation/source_integrity.json').read_text(encoding='utf-8'))
    for name, expected in manifest['files'].items():
        path = ROOT / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            errors.append(f'Не совпал SHA256 исходника: {name}')

    files = [p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    # Локальная .venv не относится к репозиторию и не проверяется.
    files = [p for p in files if not any(part in {'.git', '.venv', 'build', 'install', 'log', 'demo_results', 'ru_validation_run'} for part in p.relative_to(ROOT).parts)]
    counts = {'python': 0, 'json': 0, 'xml': 0, 'links': 0}
    for path in files:
        name = str(path.relative_to(ROOT))
        try:
            if path.suffix == '.py':
                ast.parse(path.read_text(encoding='utf-8'), filename=name)
                counts['python'] += 1
            elif path.suffix == '.json':
                json.loads(path.read_text(encoding='utf-8'))
                counts['json'] += 1
            elif path.suffix in {'.xml', '.svg'}:
                ET.parse(path)
                counts['xml'] += 1
            elif path.suffix == '.md':
                text = re.sub(r'```.*?```', '', path.read_text(encoding='utf-8'), flags=re.S)
                for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text):
                    target = target.strip().split(' "', 1)[0].strip('<>')
                    parsed = urlsplit(target)
                    if parsed.scheme or parsed.netloc or not parsed.path:
                        continue
                    local = (path.parent / unquote(parsed.path)).resolve()
                    if not local.exists():
                        errors.append(f'Нерабочая локальная ссылка: {name} -> {target}')
                    counts['links'] += 1
        except (ValueError, SyntaxError, ET.ParseError, UnicodeError) as exc:
            errors.append(f'Ошибка разбора {name}: {exc}')

    cfg_path = ROOT / 'src/foreign_object_detector/foreign_object_detector/config/production.yaml'
    try:
        cfg = json.loads(cfg_path.read_text())
        if cfg['direct'] != {'b1': True, 'b2': True, 'memoize_refinement': True} or cfg['short_extension']['enabled']:
            errors.append('Рабочие флаги не соответствуют поставке')
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f'Конфигурация: {exc}')

    # Материалы формы передаются отдельно, исходники остаются компактными.
    for folder in ('presentation', 'presentation_handoff_ru', 'media'):
        if (ROOT / folder).exists():
            errors.append(f'Лишние материалы в исходном репозитории: {folder}/')

    result = {
        'status': 'PASS' if not errors else 'FAIL',
        'runtime_hashes_checked': len(manifest['files']),
        'syntax_and_links': counts,
        'presentation_and_video': 'Передаются отдельно',
        'errors': errors,
        'scope': 'Файлы, исходники, синтаксис, локальные ссылки и разделение поставки. Docker/ROS и эталонные облака не запускались этим скриптом.',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == '__main__':
    raise SystemExit(main())
