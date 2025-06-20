import logging
from types import SimpleNamespace

import pytest

from logger import start_logger
from logger.extras.dependency import DependencyManager
from logger.extras.network import NetworkMonitor
import logger.extras.dependency as dependency_mod
import logger.extras.network as network_mod
import logger.extras.metrics as metrics
import logger.extras.utils.timer as timer_utils


def test_dependency_manager_cache(monkeypatch):
    dm = DependencyManager()

    fake_pkg = type('Dist', (), {'key': 'requests', 'version': '1.0'})
    monkeypatch.setattr(dependency_mod.pkg_resources, 'working_set', [fake_pkg], raising=False)

    t = [0.0]
    monkeypatch.setattr(dependency_mod.time, 'time', lambda: t[0])
    info1 = dm.get_environment_info()
    t[0] += 10
    info2 = dm.get_environment_info()
    assert info1 is info2
    t[0] += dm._cache_duration + 1
    info3 = dm.get_environment_info()
    assert info3 is not info1


def test_logger_log_environment(tmp_path, caplog, monkeypatch):
    logger = start_logger('env', log_dir=str(tmp_path), console_level='INFO')
    dummy_info = {
        'python': {
            'version': '3.x',
            'implementation': 'CPython',
            'compiler': '',
            'build': ('', '')
        },
        'system': {
            'os': 'Linux',
            'release': '5',
            'machine': 'x86',
            'processor': 'CPU',
            'node': 'node'
        },
        'packages': {'requests': '1.0'}
    }
    monkeypatch.setattr(logger._dep_manager, 'get_environment_info', lambda force_update=False: dummy_info)

    block = logger.log_environment(return_block=True)
    assert 'AMBIENTE' in block

    with caplog.at_level(logging.INFO):
        logger.log_environment()
    assert any('AMBIENTE' in rec.message for rec in caplog.records)
    logger.end()


def test_network_monitor_measure_latency(monkeypatch):
    nm = NetworkMonitor()

    class FakeResp:
        status_code = 200
        content = b'OK'

    t = [0.0]
    def fake_time():
        return t[0]
    monkeypatch.setattr(network_mod.time, 'time', fake_time)

    t[0] = 0
    def fake_get(url, timeout=1.0):
        t[0] = 0.05
        return FakeResp()
    monkeypatch.setattr(network_mod.requests, 'get', fake_get)
    result = nm.measure_latency('http://example.com')
    assert result['status_code'] == 200
    assert result['content_size'] == 2
    assert abs(result['latency'] - 50) < 1e-6
    metrics = nm.metrics['example.com']
    assert metrics['total_requests'] == 1
    assert metrics['total_bytes'] == 2
    assert metrics['latencies'] == [50]


def test_logger_check_connectivity_and_metrics(tmp_path, caplog, monkeypatch):
    logger = start_logger('net', log_dir=str(tmp_path), console_level='INFO')

    dummy_nm = SimpleNamespace()
    dummy_nm.check_connection = lambda host='8.8.8.8', port=53, timeout=1.0: (True, 20.0)
    dummy_nm.measure_latency = lambda url, timeout=1.0: {'latency': 30.0, 'status_code': 200, 'content_size': 2}
    dummy_nm.metrics = {'example.com': {'total_requests': 1, 'total_errors': 0, 'total_bytes': 2, 'latencies': [30.0]}}
    monkeypatch.setattr(logger, '_net_monitor', dummy_nm, raising=False)

    with caplog.at_level(logging.INFO):
        logger.check_connectivity('http://example.com')
    assert any('example.com' in rec.message for rec in caplog.records)

    metrics = logger.get_network_metrics('example.com')
    assert metrics['average_latency'] == 30.0
    logger.end()


def test_metrics_tracker_and_timer(tmp_path, caplog, monkeypatch):
    logger = start_logger('metrics', log_dir=str(tmp_path), console_level='INFO')

    t = [0.0]
    monkeypatch.setattr(metrics.time, 'time', lambda: t[0])
    monkeypatch.setattr(timer_utils.time, 'time', lambda: t[0])

    logger.reset_metrics()
    with caplog.at_level(logging.INFO):
        with logger.timer('task'):
            t[0] += 2
        logger.report_metrics()

    messages = ' '.join(r.message for r in caplog.records)
    assert 'Iniciando task' in messages
    assert 'task concluída em 2.0s' in messages
    assert 'Duração total: 2.0s' in messages
    logger.end()

