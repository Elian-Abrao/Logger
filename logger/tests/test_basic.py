"""Testes unitários para o pacote ``logger``"""

from pathlib import Path
import logging

from logger import start_logger


def test_start_logger_creates_log_files(tmp_path):
    """Verifica se ``start_logger`` devolve um ``Logger`` configurado."""
    logger = start_logger(
        "Test",
        log_dir=str(tmp_path),
        console_level="CRITICAL",  # evita poluir a saída de testes
    )

    logger.info("hello")
    logger.end()

    assert Path(logger.log_path).is_file()
    assert Path(logger.debug_log_path).is_file()
    assert hasattr(logger, "progress")


def test_progress_bar_usage(tmp_path):
    """Garante o funcionamento da progress bar ao iterar sobre um gerador."""
    logger = start_logger(
        "Progress",
        log_dir=str(tmp_path),
        console_level="CRITICAL",
    )

    gen = logger.progress(range(3), desc="Iter")
    assert hasattr(gen, "__iter__")
    itens = list(gen)
    assert itens == [0, 1, 2]
    assert getattr(logger, "_active_pbar", None) is None

    logger.end()


def test_profiling_hidden_by_default(tmp_path, caplog):
    logger = start_logger('prof0', log_dir=str(tmp_path), console_level='INFO')
    with caplog.at_level(logging.INFO):
        logger.end()
    assert not any('PROFILING' in r.message for r in caplog.records)


def test_profiling_enabled(tmp_path, caplog):
    logger = start_logger('prof1', log_dir=str(tmp_path), console_level='INFO', show_profiling=True)
    with caplog.at_level(logging.INFO):
        logger.end()
    assert any('PROFILING' in r.message for r in caplog.records)
