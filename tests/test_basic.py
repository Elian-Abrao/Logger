import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
"""Tests for the logger package."""

from logger import start_logger


def test_basic_logging(tmp_path, capsys):
    log_file = tmp_path / "log.txt"
    logger = start_logger("test", log_file)
    logger.info("mensagem")

    captured = capsys.readouterr()
    assert "mensagem" in captured.err
    assert log_file.exists()
