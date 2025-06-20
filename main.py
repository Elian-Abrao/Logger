"""Exemplo de uso do logger estruturado."""

from logger import start_logger

def main():
    logger = start_logger("Demo")

    logger.info("Processo iniciado")

    for i in logger.progress(range(5), desc="Trabalhando"):
        logger.success("testeee")
        logger.sleep(0.2)
        logger.debug("testeee")

    print("Mensagem exemplo")


if __name__ == "__main__":
    main()
