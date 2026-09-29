# Словарь параметров

Значения соответствуют рабочему файлу `production.yaml`. Профиль положения и настройки читаются из конфигурации; имя bag не выбирает поведение ядра.

| Ключ | Значение | Смысл |
|---|---|---|
| `normal.sensor.pose_mode` | `"auto_with_fallback"` | режим оценки положения |
| `normal.sensor.fallback_profile` | `"default"` | резервный профиль положения |
| `normal.sensor.max_input_range_m` | `180.0` | максимальная обрабатываемая дальность входа, м |
| `normal.pose_profiles.default.height_m` | `1.088` | высота, м |
| `normal.pose_profiles.default.lateral_angle_deg` | `0.1` | поперечный угол, градусы |
| `normal.pose_profiles.default.forward_angle_deg` | `-0.27` | продольный угол, градусы |
| `normal.pose_profiles.default.heading_deg` | `0.0` | курс, градусы |
| `normal.pose_profiles.default.center_offset_m` | `0.0` | смещение центра, м |
| `normal.pose_profiles.obstacle_recording.height_m` | `1.503` | высота, м |
| `normal.pose_profiles.obstacle_recording.lateral_angle_deg` | `-3.45` | поперечный угол, градусы |
| `normal.pose_profiles.obstacle_recording.forward_angle_deg` | `-0.93` | продольный угол, градусы |
| `normal.pose_profiles.obstacle_recording.heading_deg` | `0.0` | курс, градусы |
| `normal.pose_profiles.obstacle_recording.center_offset_m` | `0.0` | смещение центра, м |
| `normal.rail.near_min_m` | `5.0` | начало ближней области, м |
| `normal.rail.near_max_m` | `20.0` | конец ближней области, м |
| `normal.rail.slice_m` | `0.5` | шаг срезов, м |
| `normal.rail.search_half_width_m` | `3.0` | полуширина поиска, м |
| `normal.rail.height_search_m` | `[-2.5, 0.0]` | область поиска по высоте, м |
| `normal.rail.ransac_trials` | `1500` | число проб RANSAC |
| `normal.rail.separation_min_m` | `1.35` | минимальное разделение рельсов, м |
| `normal.rail.separation_max_m` | `1.85` | максимальное разделение рельсов, м |
| `normal.rail.max_plane_rms_m` | `0.025` | предельная RMS плоскости, м |
| `normal.rail.max_normalized_head_rms_m` | `0.05` | предельная RMS нормализованных головок, м |
| `normal.centerline.slice_length_m` | `5.0` | длина среза, м |
| `normal.centerline.max_range_m` | `150.0` | предельная область оценки, м |
| `normal.centerline.model_degree` | `2` | степень модели |
| `normal.centerline.max_gap_m` | `10.0` | предельный разрыв, м |
| `normal.centerline.max_extrapolation_m` | `2.0` | предельная исходная экстраполяция, м |
| `normal.centerline.search_radius_m` | `0.3` | радиус поиска, м |
| `normal.centerline.height_search_m` | `0.18` | область поиска по высоте, м |
| `normal.centerline.max_height_innovation_m` | `0.06` | предельная инновация высоты, м |
| `normal.centerline.max_pair_height_difference_m` | `0.1` | предельный перепад высоты пары, м |
| `normal.centerline.max_separation_error_m` | `0.12` | предельная ошибка разделения, м |
| `normal.centerline.max_fit_residual_m` | `0.1` | предельная невязка, м |
| `normal.centerline.min_points_per_rail` | `3` | минимум точек на рельс |
| `normal.clearance.width_m` | `2.1` | ширина габарита, м |
| `normal.clearance.height_m` | `3.0` | высота, м |
| `normal.clearance.lateral_margin_m` | `0.0` | поперечный запас, м |
| `normal.clearance.vertical_margin_m` | `0.0` | вертикальный запас, м |
| `normal.structure_mask.rail_enabled` | `true` | включение маски рельсов |
| `normal.structure_mask.rail_lateral_radius_m` | `0.1` | поперечный радиус маски, м |
| `normal.structure_mask.rail_vertical_radius_m` | `0.04` | вертикальный радиус маски, м |
| `normal.structure_mask.below_rail_enabled` | `true` | включение маски ниже рельса |
| `normal.structure_mask.below_rail_ceiling_m` | `-0.04` | верхняя граница маски ниже рельса, м |
| `normal.candidate.min_points` | `3` | минимум точек компоненты |
| `normal.candidate.min_occupied_cells` | `2` | минимум занятых ячеек |
| `normal.candidate.min_above_rail_height_m` | `0.04` | минимальная высота над рельсом, м |
| `normal.candidate.min_above_rail_points` | `3` | минимум точек выше рельса |
| `normal.candidate.range_bands_m` | `[0.0, 50.0, 100.0, 180.0]` | границы полос дальности, м |
| `normal.candidate.cell_sizes_m` | `[[0.4, 0.15, 0.15], [0.7, 0.22, 0.3], [1.0, 0.3, 0.4]]` | размеры ячеек по полосам, м |
| `normal.candidate.boundary_distance_m` | `0.1` | расстояние до границы, м |
| `sparse.nominal_scan_s` | `0.1` | номинальный интервал скана, с |
| `sparse.max_delta_d_m` | `0.2` | предельное поперечное изменение, м |
| `sparse.max_delta_h_m` | `0.2` | предельное изменение высоты, м |
| `sparse.approach_per_scan_min_m` | `-0.5` | минимальное приближение за скан, м |
| `sparse.approach_per_scan_max_m` | `3.0` | максимальное приближение за скан, м |
| `sparse.max_approach_innovation_m` | `1.0` | предельная инновация приближения, м |
| `sparse.history_positions` | `5` | число позиций истории |
| `sparse.max_missing_frames` | `1` | максимум пропущенных кадров |
| `sparse.rules` | `["S0", "S1", "S2", "S3"]` | доступные правила подтверждения |
| `sparse.emit_on_missing` | `false` | выдача подтверждения на пропуске |
| `sparse.require_above_existing_height_evidence` | `true` | требование исходных высотных свидетельств |
| `sparse_rule` | `"S2"` | выбранное правило разреженного подтверждения |
| `phase4c_payload_sha256` | `"c1b1f9fdd521e76d6d31c2e22ee8697678ce89ba36842c248483aadfbaa4f016"` | SHA256 исходных параметров |
| `ros.input_topic` | `"/lidar_points"` | Имя ROS-топика |
| `ros.obstacle_topic` | `"/foreign_object/obstacle"` | Имя ROS-топика |
| `ros.distance_topic` | `"/foreign_object/distance"` | Имя ROS-топика |
| `ros.state_topic` | `"/foreign_object/state"` | Имя ROS-топика |
| `ros.horizon_topic` | `"/foreign_object/horizon"` | Имя ROS-топика |
| `ros.processing_topic` | `"/foreign_object/processing_ms"` | Имя ROS-топика |
| `ros.quality_topic` | `"/foreign_object/track_quality"` | Имя ROS-топика |
| `debug` | `false` | полная диагностика |
| `far_synthetic.enabled` | `true` | включение ветви |
| `short_extension.enabled` | `false` | включение ветви |
| `short_extension.model` | `"local_quadratic"` | модель продолжения |
| `short_extension.maximum_extension_m` | `5.0` | максимальное дополнительное продолжение, м |
| `direct.b1` | `true` | ветвь измеренной геометрии |
| `direct.b2` | `true` | номинальная переходная ветвь |
| `direct.memoize_refinement` | `true` | повторное использование уточнения внутри кадра |

Замороженный frozen_far.json содержит таблицу 128 углов лучей (beam_elevations_deg), источник ее SHA256 (beam_source_sha256), начало (origin), вращение (rotation) и constants. Порог beam_error_strict_gt_deg: строго больше 0.02°, canonical_forward_min_m: 60 м, range_max_m: 180 м, strong_half_width_m: 0.95 м, strong_lower_m: 0.06 м, strong_upper_m: 2.9 м. Матрицы и таблица сохраняются побайтно.
