"""Example usage of the logger package."""

import time
from logger import start_logger


def main() -> None:
    log = start_logger("demo", "demo.log")
    log.info("Inicio do processo")

    with log.timer("processamento"):
        for i in log.progress(range(5), desc="Trabalhando"):
            time.sleep(0.2)
            log.debug(f"Item {i}")

    log.info("Fim do processo")


if __name__ == "__main__":
    main()
