# Развертывание и демонстрация

Цель: Ubuntu 22.04, ROS 2 Humble, linux/amd64. Dockerfile закрепляет исходный digest ROS и сборку C++17. Runtime содержит зависимости и работает без сети. Сборка без кэша требует доступных apt-зависимостей; передаваемый docker save позволяет обойти сборку.

Основной запуск описан в README. Всегда `--shm-size=256m`, исходный профиль Fast DDS и один поток BLAS. XML профиля не менялся. Контейнер не содержит эталоны, метки, raw bags или исследовательские зависимости.

На Linux внешний ROS-публикатор требует общей достижимой DDS-сети, совпадающего ROS_DOMAIN_ID и совместимого QoS. В Docker Desktop используйте один контейнер для узла, плеера и наблюдателя через docker exec. Сценарии demo_real.sh/demo_synthetic.sh выполняют эту схему внутри контейнера с `--network none`. Bag монтируется read-only.

Перед плеером сценарий выполняет ros2 bag info, проверяет topic и ожидает подписку узла. Затем ограниченно проигрывает bag и записывает фактические сообщения. Layout16 содержит XYZ/intensity; layout26 дополнительно ring/timestamp. Адаптер читает поля динамически, а не выбирает поведение только по размеру.

Пауза: сохраненное сообщение не становится текущим. Наблюдатель свежести должен сообщить UNKNOWN. Возобновление с разрывом timestamp сбрасывает S2. Повтор bag с более ранним timestamp вызывает TIMESTAMP_ROLLBACK. Неправильный topic дает отсутствие входа, а не доказательство CLEAR. Поврежденный cloud вызывает INPUT_ERROR, TRACK_UNRELIABLE, distance=-1 и сброс истории. После исправления topic/config перезапустите узел и дождитесь свежих выходов.

Резерв через тот же установленный executable:

```bash
docker run --rm --platform linux/amd64 --network host --shm-size=256m lidar-near:v5-query-first-ru ros2 launch foreign_object_detector detector.launch.py config:=/opt/detector/install/foreign_object_detector/lib/python3.10/site-packages/foreign_object_detector/config/v4_fallback.yaml
```

Исходный `lidar-near:v4-direct` и исходный `lidar-near:v5-query-first` сохранены. Их идентичности лежат в manifests общей поставки.
