# Автономная проверка

Скачайте полный `lct26_task5_validation_ru.tar.gz` и Docker-образ из [Release](https://github.com/bq777xCube/lidar_project/releases/tag/submission-2026-09-28). Они содержат все требуемые неизменные эталоны и исходники. Скрипты в этой папке сохранены для просмотра; без содержимого архива рядом с ними не хватает зависимостей.

```bash
mkdir verification
cd verification
# Поместите сюда скачанные архивы и SHA256SUMS.
shasum -a 256 -c SHA256SUMS
gzip -dc lidar-near-v5-query-first-ru-amd64.tar.gz | docker load
tar -xzf lct26_task5_validation_ru.tar.gz
bash validation/validate_ru.sh "$PWD/ru_validation_run"
```

SHA256SUMS перечисляет четыре архива: для проверки всего списка скачайте все четыре. На Linux также доступна команда `sha256sum -c SHA256SUMS`.
