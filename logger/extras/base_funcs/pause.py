"""pause.py - Pausa interativa para o logger."""

from logging import Logger

__all__ = ["pause"]


def pause(self: Logger, msg: str = "Digite algo para continuar... ") -> str:
    """Exibe mensagem e aguarda entrada do usuário."""
    resp = input(msg)
    self.debug(f"Resposta do usuário: {resp}")
    return resp
