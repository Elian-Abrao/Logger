"""context.py - Gerenciamento de contexto e profiling para o logger.

Este modulo fornece suporte a contextos hierarquicos e profiling de funcoes.
Uso:
    from logger.core.context import ContextManager, Profiler, logger_context
"""

from contextlib import contextmanager
from contextvars import ContextVar
from logging import Logger
from typing import Optional, Callable, Any
import cProfile
import pstats
import io
import functools

# Variavel de contexto global para rastreamento da pilha de contextos
_log_context = ContextVar('log_context', default=[])

class ContextManager:
    """Gerencia contextos hierarquicos para o logger."""
    def __init__(self):
        self._context_separator = ' → '

    def get_current_context(self) -> str:
        contexts = _log_context.get()
        return self._context_separator.join(contexts) if contexts else ''

    @contextmanager
    def context(self, name: str):
        token = _log_context.set(_log_context.get() + [name])
        try:
            yield
        finally:
            _log_context.reset(token)

# --- Funcoes utilitarias ligadas ao logger ---

def logger_context(self: Logger, name: str) -> contextmanager:
    """Adiciona contexto temporario aos logs."""
    @contextmanager
    def context_wrapper():
        with self._context_manager.context(name):
            yield
    return context_wrapper()

def log_with_context(self: Logger, level, msg, args, **kwargs):
    """Inclui o contexto atual nas mensagens de log."""
    context = self._context_manager.get_current_context()
    if context:
        msg = f"[{context}] {msg}"
    self._original_log(level, msg, args, **kwargs)

class Profiler:
    """Gerenciador simples para profiling utilizando cProfile."""
    def __init__(self):
        self.profiler = None
        self._active = False

    def start(self) -> None:
        if not self._active:
            self.profiler = cProfile.Profile()
            self.profiler.enable()
            self._active = True

    def stop(self) -> str:
        if not self._active:
            return "Profiler não está ativo"
        self.profiler.disable()
        self._active = False
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)
        return s.getvalue()

# --- Wrappers de profiling ---

@contextmanager
def logger_profile_cm(self: Logger, name: str = None) -> None:
    section_name = name or 'Seção'
    self.info(f"🔍 Iniciando profiling: {section_name}")
    self._profiler.start()
    try:
        yield
    finally:
        report = self._profiler.stop()
        self.info(f"📊 Resultado do profiling ({section_name}):\n{report}")

def logger_profile(self: Logger, func: Optional[Callable] = None, *, name: str = None) -> Any:
    if func is None:
        return logger_profile_cm(self, name)
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with logger_profile_cm(self, func.__name__):
            return func(*args, **kwargs)
    return wrapper

def _setup_context_and_profiling(logger: Logger) -> None:
    """Configura suporte a contexto e profiling na instancia do logger."""
    context_manager = ContextManager()
    profiler = Profiler()
    setattr(logger, '_context_manager', context_manager)
    setattr(logger, '_profiler', profiler)
    setattr(logger, '_original_log', logger._log)
    setattr(Logger, '_log', log_with_context)
    setattr(Logger, 'context', logger_context)
    setattr(Logger, 'profile', logger_profile)
    setattr(Logger, 'profile_cm', logger_profile_cm)
