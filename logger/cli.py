"""cli.py
--------
Nome: CLI
Descricao: Interface de linha de comando para inicializar o logger.
Funcionalidades: Permite configurar nome, arquivo de log e nivel pelo terminal.
Uso:
    python -m logger.cli --name app --file app.log
"""

import argparse
from pathlib import Path
from .core import start_logger


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Demo logger CLI")
    parser.add_argument("--name", default="app", help="Nome do logger")
    parser.add_argument("--file", type=Path, help="Arquivo de log")
    parser.add_argument("--level", default="INFO", help="Nivel de log")
    ns = parser.parse_args(args)

    logger = start_logger(ns.name, ns.file, getattr(__import__('logging'), ns.level.upper(), 20))
    logger.info("Logger iniciado pela CLI")


if __name__ == "__main__":
    main()
