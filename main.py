"""Exemplo de uso do logger estruturado."""

from logger import start_logger


def main():
    logger = start_logger("Demo")
    logger.start()
    logger.info("Processo iniciado")
    with logger.context("Etapa"):  # from context module via start_logger
        with logger.timer("demo"):
            for i in logger.progress(range(5), desc="Trabalhando"):
                logger.success("testeee")
                logger.sleep(0.2)
    logger.capture_prints(True)
    print("Mensagem exemplo")
    logger.capture_prints(False)
    logger.end()


if __name__ == "__main__":
    main()
