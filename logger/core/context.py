"""context.py - Gerenciamento de contexto e profiling para o logger.

Este modulo fornece suporte a contextos hierarquicos e profiling de funcoes.
Uso:
    from logger.core.context import ContextManager, Profiler, logger_context
"""

from contextlib import contextmanager
from contextvars import ContextVar
from logging import Logger
from typing import Callable, Any, Optional, ContextManager as TypingContextManager, Iterator
import cProfile
import functools
import io
import pstats
from logger.extras.progress import format_block

# Armazena o método original de logging antes de qualquer monkey patch
_original_log_method = Logger._log

# Variavel de contexto global para rastreamento da pilha de contextos
_log_context: ContextVar[list[str]] = ContextVar('log_context', default=[])

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

def logger_context(self: Logger, name: str) -> TypingContextManager[None]:
    """Adiciona contexto temporario aos logs."""
    @contextmanager
    def context_wrapper():
        with self._context_manager.context(name):
            yield
    return context_wrapper()

def log_with_context(self: Logger, level, msg, args, **kwargs):
    """Inclui o contexto atual nas mensagens de log se disponível."""
    context_manager = getattr(self, '_context_manager', None)
    if context_manager:
        context = context_manager.get_current_context()
        if context:
            msg = f"[{context}] {msg}"
    original = getattr(self, '_original_log', _original_log_method)
    original(self, level, msg, args, **kwargs)

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

    def _build_chain(
        self,
        func: tuple[str, int, str],
        stats: dict,
        depth: int = 3,
    ) -> list[tuple[str, int, str]]:
        if depth <= 0:
            return [func]
        callers = stats.get(func, (0, 0, 0.0, 0.0, {}))[4]
        if not callers:
            return [func]
        best = max(callers.items(), key=lambda kv: kv[1][3])[0]
        return self._build_chain(best, stats, depth - 1) + [func]

    def get_report_lines(self, limit: int = 10) -> list[str]:
        """Linhas de profiling ordenadas por tempo acumulado em português."""
        if not self.profiler:
            return []
        ps = pstats.Stats(self.profiler)
        ps.calc_callees()
        stats_dict: dict = getattr(ps, "stats", {})  # type: ignore[attr-defined]
        items = []
        for func, (cc, nc, tt, ct, callers) in stats_dict.items():
            items.append((ct, tt, nc, func))
        items.sort(reverse=True)
        lines = []
        for ct, tt, nc, func in items[:limit]:
            chain = self._build_chain(func, stats_dict)
            names = " → ".join(f[2] for f in chain)
            lines.append(
                f"{names} | chamadas: {nc} | acumulado: {ct:.3f}s | próprio: {tt:.3f}s"
            )
        return lines

# --- Wrappers de profiling ---

@contextmanager
def logger_profile_cm(self: Logger, name: str | None = None) -> Iterator[None]:
    section_name = name or 'Seção'
    self.info(f"🔍 Iniciando profiling: {section_name}")
    self._profiler.start()  # type: ignore[attr-defined]
    try:
        yield
    finally:
        report = self._profiler.stop()  # type: ignore[attr-defined]
        self.info(f"📊 Resultado do profiling ({section_name}):\n{report}")

def logger_profile(
    self: Logger,
    func: Optional[Callable] = None,
    *,
    name: str | None = None,
) -> Any:
    if func is None:
        return logger_profile_cm(self, name)
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with logger_profile_cm(self, func.__name__):
            return func(*args, **kwargs)
    return wrapper


def logger_profile_report(
    self: Logger,
    *,
    limit: int = 10,
    level: str = "INFO",
    return_block: bool = False,
) -> str | None:
    """Gera um resumo do profiling executado com rótulos em português."""
    self._profiler.stop()  # type: ignore[attr-defined]
    lines = self._profiler.get_report_lines(limit)  # type: ignore[attr-defined]
    if not lines:
        return None
    block = format_block("PROFILING", lines)
    if return_block:
        return block
    getattr(self, level.lower())(f"\n{block}", extra={"plain": True, "file_only": True})
    return None

def _setup_context_and_profiling(logger: Logger) -> None:
    """Configura suporte a contexto e profiling na instancia do logger."""
    context_manager: ContextManager = ContextManager()
    profiler = Profiler()

    # guarda instancias no logger
    setattr(logger, '_context_manager', context_manager)
    setattr(logger, '_profiler', profiler)

    # Salva o metodo original apenas na primeira execucao
    if not hasattr(logger, '_original_log'):
        setattr(logger, '_original_log', _original_log_method)

    # Aplica wrappers na classe para permitir uso pelos loggers criados
    Logger._log = log_with_context  # type: ignore[assignment]
    setattr(Logger, 'context', logger_context)
    setattr(Logger, 'profile', logger_profile)
    setattr(Logger, 'profile_cm', logger_profile_cm)
    setattr(Logger, 'profile_report', logger_profile_report)
