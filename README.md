# Обнаружение посторонних предметов по облаку LiDAR

Итоговое решение для обнаружения посторонних предметов по облаку LiDAR. Готовый контейнер: `lidar-near:v5-query-first-ru`.

## Готовые материалы

- [Release: образ и все архивы](https://github.com/bq777xCube/lidar_project/releases/tag/submission-2026-09-28).
- [Документация](docs/ARCHITECTURE_RU.md), [обзор PDF](docs/Обзор_решения.pdf).
- [Пакет автору презентации](presentation_handoff_ru/НАЧАТЬ_ЗДЕСЬ.md).
- [Видео реального воспроизведения bag](media/Демонстрация.mp4).
- [Ссылки для формы](SUBMISSION_LINKS.md), [статус размещения](PUBLICATION_STATUS.json).

Репозиторий приватный. Ссылки доступны только пользователям с правами на него; доступ экспертам отдельно не выдавался. Финальная презентация еще не оформлена. Архивы Release содержат уточненные подписи сравнения в документации. Алгоритм и образ сохранены. Контрольные суммы исходных локальных пакетов сохранены в downloads/sealed_delivery_receipt.json, исторический статус — в downloads/SEALED_DELIVERY_STATUS.json. Текущее состояние размещения отражает PUBLICATION_STATUS.json.

## Быстрый запуск

Из корня этого репозитория, при установленном Docker:

```bash
docker build --platform linux/amd64 -t lidar-near:v5-query-first-ru .
bash scripts/demo_synthetic.sh /absolute/path/to/cloud_with_fake_obj
```

Сценарий запускает установленный узел, проверяет наличие `/lidar_points` в bag и готовность подписчика, затем выполняет `ros2 bag play`. Данные монтируются только для чтения. Семь выходных топиков и наблюдаемые облака сохраняются в новом локальном каталоге `demo_results/`. Скорость демонстрации синтетики по умолчанию 0.1x, реальных данных 0.2x. Это корректностная демонстрация в локальной amd64-эмуляции, не измерение производительности целевого i7.

Для собственного публикатора на Linux:

```bash
docker run --rm --platform linux/amd64 --network host --shm-size=256m lidar-near:v5-query-first-ru
# В другом терминале с ROS 2 Humble, тем же ROS_DOMAIN_ID и совместимым DDS:
ros2 bag play /absolute/path/to/bag --topics /lidar_points --read-ahead-queue-size 8
ros2 topic echo /foreign_object/state
```

На macOS используйте сценарии: узел и плеер работают в одном контейнере. `--network host` не является универсальной схемой Docker Desktop. Для ручной работы в этом же контейнере применяйте `docker exec ... /detector_entrypoint.sh ros2 ...`.

Если образ передан отдельно, сборка не требуется: `gzip -dc lidar-near-v5-query-first-ru-amd64.tar.gz | docker load`. При первом build нужна база и системные зависимости либо готовый кэш. Во время работы алгоритм ничего не загружает из сети.

## Результат и границы

`/foreign_object/obstacle`, `/distance`, `/state`, `/horizon`, `/processing_ms`, `/track_quality`, `/source` имеют общий префикс `/foreign_object`. `distance=-1` означает отсутствие подтвержденного расстояния, а не свободный путь. `TRACK_UNRELIABLE` означает ненадежную геометрию. Старые сообщения без timestamp нельзя считать текущим результатом.

Ближний канал использует рельсовую геометрию и исходный S2. Дальний канал и B1/B2 используют несовместимость синтетических вставок с направлениями лучей. A/+5 м выключен. На прямо проверенных примерах предоставленных синтетических данных обнаружение продемонстрировано примерно до 100 м. Это не гарантия для любых реальных препятствий. Нейронная модель не входит в алгоритм.

## Документы и проверка

- [Архитектура](docs/ARCHITECTURE_RU.md), [алгоритм и параметры](docs/ALGORITHM_RU.md).
- [Результаты и ограничения](docs/RESULTS_RU.md), [API](docs/API_RU.md).
- [Развертывание](docs/DEPLOYMENT_RU.md), [автономная проверка](docs/VALIDATION_RU.md).
- [Сдача](docs/SUBMISSION_RU.md), [лицензии](docs/LICENSES_RU.md).

Для автономной проверки распакуйте отдельный `lct26_task5_validation_ru.tar.gz` и выполните `bash validation/validate_ru.sh "$PWD/ru_validation_run"`. Исходный рабочий каталог разработки не нужен. Эталоны не входят в runtime image.

Записи демонстрации и пакет коллеге поставляются отдельно. Финальная презентация и внешние ссылки требуют действий команды; статус указан в PUBLICATION_STATUS.json.
