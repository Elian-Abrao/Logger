import os
from logger import start_logger

def test_start_logger(tmp_path):
    logdir = tmp_path / "logs"
    logger = start_logger("test", log_dir=str(logdir))
    logger.start()
    logger.info("ok")
    logger.end()
    assert os.path.exists(logger.log_path)
