# ROS API

Вход `/lidar_points`: `sensor_msgs/msg/PointCloud2`. XYZ float32/float64 читаются по полям; порядок и stride проверяет адаптер. ROS header.stamp определяет причинную последовательность S2. Частота выхода зависит от фактически принятых и обработанных входов, не от таймера 10 Гц.

| Топик | Тип | Значение |
|---|---|---|
| /foreign_object/obstacle | std_msgs/msg/Bool | Подтвержденное препятствие в текущем результате |
| /foreign_object/distance | std_msgs/msg/Float32 | Метры; -1 при отсутствии подтвержденного расстояния |
| /foreign_object/state | std_msgs/msg/String | Состояние решения |
| /foreign_object/horizon | std_msgs/msg/Float32 | Измеренный поддержанный горизонт, м; -1 при ошибке входа |
| /foreign_object/processing_ms | std_msgs/msg/Float32 | Время обработки callback, мс, не полная задержка доставки |
| /foreign_object/track_quality | std_msgs/msg/String | Качество рельсовой геометрии |
| /foreign_object/source | std_msgs/msg/String | Источник выбранного решения; пустая строка допустима |

Машинные коды сохранены: CLEAR означает отсутствие подтверждения в доступной области; TRACK_UNRELIABLE означает ненадежную опору и не равен CLEAR; OBSTACLE_NORMAL означает обычное подтверждение, OBSTACLE_SPARSE означает подтверждение S2. NEAR_NORMAL, NEAR_SPARSE, FAR_SYNTHETIC_BEAM, SYNTHETIC_MEASURED и SYNTHETIC_NOMINAL_BRIDGE указывают ветвь (полный перечень реально используемых строк: CONTRACT_STRINGS_RU.md). GOOD/DEGRADED/INVALID описывают качество. TIMESTAMP_ROLLBACK означает возврат времени назад, TIMESTAMP_GAP/FRAME_GAP разрыв, INPUT_ERROR ошибку входа.

Семь выходов не имеют общей временной метки и не являются атомарным пакетом. Получатель обязан контролировать свежесть и не объединять старую дальность с новым состоянием как гарантированную пару. Операторский `watch_outputs.py` проверяет поступление трех основных выходов; при отсутствии свежих сообщений завершает работу с кодом 2 и UNKNOWN. Это наблюдатель, а не timeout-публикатор внутри узла. Остановка плеера не публикует автоматически CLEAR.

Параметры узла: config (путь), input_topic (переопределение), debug (диагностика). Изменение параметров пересоздает детектор и сбрасывает S2. Строки логов/исключений сохранены для совместимости проверок, русский смысл описан здесь.
