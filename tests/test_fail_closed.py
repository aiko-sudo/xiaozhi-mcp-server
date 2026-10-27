"""Regression: device failure must not become simulated success."""
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from tool_registry import ToolRegistry
from adapters.radar_adapter import RadarAdapter


def test_missing_serial_fails_closed():
    with patch('serial.Serial', side_effect=OSError('offline')):
        with pytest.raises(RuntimeError, match='拒绝降级'):
            RadarAdapter(name='radar', backend='serial')


def test_http_error_fails_closed():
    with patch('requests.get', side_effect=OSError('offline')):
        with pytest.raises(RuntimeError, match='拒绝降级'):
            RadarAdapter(name='radar', backend='http')


def test_registry_never_falls_back_to_mock():
    with patch('serial.Serial', side_effect=OSError('offline')):
        with pytest.raises(RuntimeError, match='初始化失败'):
            ToolRegistry(backend='serial')


def test_explicit_mock_result_is_marked():
    r = ToolRegistry(backend='mock').call_tool('radar_check_safe', {})
    assert r['backend'] == 'mock' and r['simulated'] is True


def test_does_not_mutate_config():
    cfg = {'radar': {'backend': 'mock'}}
    ToolRegistry(backend='mock', config=cfg)
    assert cfg == {'radar': {'backend': 'mock'}}
