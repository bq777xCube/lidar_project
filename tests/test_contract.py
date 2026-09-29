"""Небольшие локальные проверки контракта. Не заменяют оценку на физических препятствиях."""
from __future__ import annotations

import copy
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

if os.environ.get('NEAPY_USE_INSTALLED') != '1':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'foreign_object_detector'))

import numpy as np
from foreign_object_detector.config import DEFAULT_CONFIG, load_config
from foreign_object_detector.detector import Detector
from foreign_object_detector.far import FarChannel
from foreign_object_detector.pointcloud_adapter import PointCloudError, xyz_from_pointcloud2


def cloud(points: np.ndarray, step: int = 16, *, big: bool = False,
          height: int = 1, padding: int = 0, offsets: tuple[int, int, int] = (0, 4, 8)) -> SimpleNamespace:
    """Собрать сообщение без импорта ROS, сохраняя фактические шаги памяти."""
    points = np.asarray(points, dtype=np.float32).reshape(-1, 3)
    if height <= 0 or len(points) % height:
        raise ValueError('Некорректная высота fixture')
    width = len(points) // height
    row = width * step + padding
    data = bytearray(row * height)
    fmt = '>f' if big else '<f'
    for idx, point in enumerate(points):
        r, c = divmod(idx, width)
        for value, offset in zip(point, offsets):
            struct.pack_into(fmt, data, r * row + c * step + offset, float(value))
    fields = [SimpleNamespace(name=n, offset=o, datatype=7, count=1) for n, o in zip('xyz', offsets)]
    if step >= 16 and offsets == (0, 4, 8):
        fields.append(SimpleNamespace(name='intensity', offset=12, datatype=7, count=1))
    if step == 26 and offsets == (0, 4, 8):
        fields += [SimpleNamespace(name='ring', offset=16, datatype=4, count=1),
                   SimpleNamespace(name='timestamp', offset=18, datatype=8, count=1)]
    return SimpleNamespace(width=width, height=height, point_step=step, row_step=row,
                           data=data, fields=fields, is_bigendian=big)


class InputContractTests(unittest.TestCase):
    """Формат PointCloud2, порядок байтов, строки и отказы на повреждении."""

    def test_supplied_layouts(self):
        points = np.array([[1, 2, 3], [-4, 0.5, 8]], dtype=np.float32)
        for step in (16, 26):
            with self.subTest(point_step=step):
                np.testing.assert_array_equal(xyz_from_pointcloud2(cloud(points, step)), points)

    def test_endian_and_row_padding(self):
        points = np.arange(18, dtype=np.float32).reshape(6, 3) / 4
        for step in (16, 26):
            for big in (False, True):
                for padding in (0, 12):
                    with self.subTest(step=step, big=big, padding=padding):
                        m = cloud(points, step, height=2, padding=padding, big=big)
                        np.testing.assert_array_equal(xyz_from_pointcloud2(m), points)

    def test_reordered_fields(self):
        p = np.array([[4.5, -1.25, 9]], dtype=np.float32)
        m = cloud(p, 28, offsets=(16, 0, 8))
        m.fields.reverse()
        np.testing.assert_array_equal(xyz_from_pointcloud2(m), p)

    def test_empty(self):
        out = xyz_from_pointcloud2(cloud(np.empty((0, 3))))
        self.assertEqual(out.shape, (0, 3))
        self.assertEqual(out.dtype, np.float32)

    def test_float64_rejected(self):
        m = cloud([[1, 2, 3]])
        m.fields[0].datatype = 8
        with self.assertRaises(PointCloudError):
            xyz_from_pointcloud2(m)

    def test_vector_field_rejected(self):
        m = cloud([[1, 2, 3]])
        m.fields[0].count = 2
        with self.assertRaises(PointCloudError):
            xyz_from_pointcloud2(m)

    def test_overlapping_fields_rejected(self):
        m = cloud([[1, 2, 3]])
        m.fields[1].offset = 2
        with self.assertRaises(PointCloudError):
            xyz_from_pointcloud2(m)

    def test_duplicate_and_missing_fields_rejected(self):
        for mode in ('duplicate', 'missing'):
            m = cloud([[1, 2, 3]])
            if mode == 'duplicate':
                m.fields.append(copy.copy(m.fields[0]))
            else:
                m.fields = [f for f in m.fields if f.name != 'z']
            with self.subTest(mode=mode), self.assertRaises(PointCloudError):
                xyz_from_pointcloud2(m)

    def test_truncated_buffer_and_invalid_row_rejected(self):
        for mode in ('buffer', 'row'):
            m = cloud([[1, 2, 3]])
            if mode == 'buffer':
                m.data = m.data[:-1]
            else:
                m.row_step = m.point_step - 1
            with self.subTest(mode=mode), self.assertRaises(PointCloudError):
                xyz_from_pointcloud2(m)

    def test_parser_preserves_placeholders(self):
        p = np.array([[0, 0, 0], [np.nan, 2, 3]], dtype=np.float32)
        out = xyz_from_pointcloud2(cloud(p))
        # Удаление заполнителей относится к ядру, не к адаптеру индексов.
        np.testing.assert_array_equal(out, p)


class ConfigurationTests(unittest.TestCase):
    def test_defaults(self):
        cfg = load_config()
        self.assertEqual(cfg['direct'], {'b1': True, 'b2': True, 'memoize_refinement': True})
        self.assertFalse(cfg['short_extension']['enabled'])
        self.assertTrue(cfg['far_synthetic']['enabled'])

    def test_fallback_config(self):
        cfg = load_config(DEFAULT_CONFIG.with_name('v4_fallback.yaml'))
        self.assertFalse(cfg['direct']['b1'])
        self.assertFalse(cfg['direct']['b2'])
        self.assertTrue(cfg['direct']['memoize_refinement'])
        self.assertFalse(cfg['short_extension']['enabled'])

    def assert_invalid_config(self, cfg):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'config.yaml'
            p.write_text(json.dumps(cfg))
            with self.assertRaises(ValueError):
                load_config(p)

    def test_numeric_threshold_change_rejected(self):
        cfg = load_config()
        cfg['normal']['clearance']['width_m'] = 2.2
        self.assert_invalid_config(cfg)

    def test_boolean_options_are_strict(self):
        cfg = load_config()
        cfg['direct']['b1'] = 1
        self.assert_invalid_config(cfg)

    def test_duplicate_topics_rejected(self):
        cfg = load_config()
        cfg['ros']['distance_topic'] = cfg['ros']['state_topic']
        self.assert_invalid_config(cfg)


class KernelSmokeTests(unittest.TestCase):
    """Детерминированные математические входы, а не оценка дальности на датасете."""

    def test_far_empty(self):
        result = FarChannel().process(np.empty((0, 3), dtype=np.float32))
        self.assertFalse(result['obstacle'])
        self.assertEqual(result['distance_m'], -1.0)

    def test_on_beam_returns(self):
        far = FarChannel()
        s = np.full(128, 100.0)
        canonical = np.column_stack((s, np.zeros(128), s * np.tan(np.radians(far.beams))))
        result = far.process(canonical, canonical=True, debug=True)
        self.assertEqual(result['offbeam_points'], 0)
        self.assertFalse(result['obstacle'])

    def test_far_rejects_below_cutoff_and_invalid(self):
        raw = np.array([[0, -59, 0], [0, 0, 0], [np.nan, -100, 0], [0, -181, 0]], dtype=np.float32)
        result = FarChannel().process(raw)
        self.assertFalse(result['obstacle'])
        self.assertEqual(result['far_input_points'], 0)

    def test_actual_fixture_point_selection(self):
        far = FarChannel()
        # Конструируем математические текущие точки, а не извлекаем скрытую разметку.
        canonical = np.column_stack((np.full(60, 100.0), np.zeros(60), np.linspace(-0.6, 0.8, 60)))
        result = far.process(canonical, canonical=True, debug=True)
        self.assertTrue(result['obstacle'])
        self.assertGreater(result['distance_m'], 0)
        selected = result['source_index']
        self.assertIn(selected, result['debug']['strong_source_indices'])
        expected = (canonical[selected] - far.origin) @ far.rotation.T
        self.assertAlmostEqual(result['distance_m'], float(expected[0]), places=10)

    def test_zero_cloud_is_unknown_not_clear(self):
        result = Detector().process(np.zeros((16, 3), dtype=np.float32), 1_000_000_000)
        self.assertFalse(result['obstacle'])
        self.assertEqual(result['distance_m'], -1.0)
        self.assertEqual(result['state'], 'TRACK_UNRELIABLE')


if __name__ == '__main__':
    unittest.main()
