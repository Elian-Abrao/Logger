import logging
from logging import Logger, Formatter, StreamHandler, FileHandler
from pathlib import Path
from datetime import datetime
from colorama import init, Fore, Style
import threading
import os
import inspect
import sys
import time
from contextlib import contextmanager
from typing import Optional, Dict, List, Tuple, Any, Callable
from collections import defaultdict
import psutil
import gc
import cProfile
import pstats
import io
import functools
from contextvars import ContextVar
import pkg_resources
import platform
import socket
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from wcwidth import wcswidth
import builtins

try:
    import pyautogui
except ImportError:
    pyautogui = None

# Inicializa o módulo colorama para permitir a exibição de cores no console do Windows.
# O parâmetro autoreset=True garante que as cores sejam resetadas automaticamente após cada uso.
def _init_colorama():
    init(autoreset=True)

# Lista de funções internas que devem ser excluídas do rastreamento da cadeia de chamadas (call chain).
# Estas funções são utilitárias do próprio logger e não devem aparecer no registro de chamadas do usuário.
_INTERNAL_FUNCS = {
    'format', '_extract_call_chain', '_init_colorama',
    '_define_custom_levels', '_setup_directories', '_get_log_filename',
    '_attach_screenshot', 'screen'
}

# Variável de contexto para rastreamento
_log_context = ContextVar('log_context', default=[])

class CustomFormatter(Formatter):
    """
    Formatter personalizado que implementa formatação avançada para logs com recursos visuais e contextuais.
    
    Características Principais:
    1. Formatação Visual:
        - Emojis únicos para cada nível de log
        - Cores distintas no console usando colorama
        - Alinhamento padronizado das mensagens
        - Espaçamento consistente entre elementos
    
    2. Informações Contextuais:
        - Nome do nível de log com cor
        - Timestamp preciso
        - Informações de thread
        - Cadeia de chamadas de funções
        - Caminho do arquivo e número da linha
    
    3. Personalização por Nível:
        DEBUG (🐛 Azul): Para informações detalhadas de desenvolvimento
        INFO (🔍 Verde): Para informações gerais do processo
        SUCCESS (✅ Ciano): Para operações bem-sucedidas
        WARNING (🚨 Amarelo): Para avisos e alertas
        ERROR (❌ Vermelho): Para erros recuperáveis
        CRITICAL (🔥 Magenta): Para erros críticos do sistema
        SCREEN (📸 Magenta): Para registrar capturas de tela
    
    4. Formatos de Saída:
        Console: "{timestamp} {emoji} [NÍVEL] - {mensagem} {thread}"
        Arquivo: "{timestamp} {emoji} [NÍVEL] - {mensagem} <> [arquivo:linha] - [funções📍] {thread}"
    
    5. Recursos Automáticos:
        - Detecção automática de thread principal
        - Formatação condicional baseada no contexto
        - Reset automático de cores após cada mensagem
        - Padding dinâmico para alinhamento
    """
    
    # Dicionário que mapeia cada nível de log para um emoji representativo
    # Facilita a identificação visual rápida do tipo de mensagem no log
    LEVEL_EMOJI = {
        'DEBUG':    '🐛',  # Bug para debugging
        'INFO':     '🔍',  # Lupa para informações
        'SUCCESS':  '✅',  # Check verde para sucesso
        'WARNING':  '🚨',  # Sirene para avisos
        'ERROR':    '❌',  # X vermelho para erros
        'CRITICAL': '🔥',  # Fogo para erros críticos
        'SCREEN':   '📸',  # Câmera para capturas de tela
    }

    # Dicionário que define as cores ANSI para cada nível de log
    # Utiliza as cores do módulo colorama para melhor visualização no console
    LEVEL_COLOR = {
        'DEBUG':    Fore.BLUE,     # Azul para debugging
        'INFO':     Fore.GREEN,    # Verde para informações
        'SUCCESS':  Fore.CYAN,     # Ciano para sucesso
        'WARNING':  Fore.YELLOW,   # Amarelo para avisos
        'ERROR':    Fore.RED,      # Vermelho para erros
        'CRITICAL': Fore.MAGENTA,  # Magenta para erros críticos
        'SCREEN':   Fore.MAGENTA,  # Magenta para capturas de tela
    }

    def format(self, record):
        # Emojis e cores
        record.emoji = self.LEVEL_EMOJI.get(record.levelname, '🔹')
        color = self.LEVEL_COLOR.get(record.levelname, '')
        record.levelname_color = f"{color}[{record.levelname}]{Style.RESET_ALL}"
        record.levelname = f"[{record.levelname}]"

        pad = 11
        record.levelpad = ' ' * (pad - len(record.levelname))

        record.thread = threading.current_thread().name
        record.thread_disp = '' if record.thread == 'MainThread' else f"[T:{record.thread}]"

        record.call_chain = _extract_call_chain(record)

        # Verifica se o log veio de fora do sistema de logger
        if "logger" not in record.pathname.lower():
            filename = Path(record.pathname).name
            record.meta = f"⮕ 📁{filename}:{record.lineno} | 🧭 {record.call_chain}"
        else:
            record.meta = ""

        # Formata a mensagem com o formatter base + metadados compactos (se houver)
        mensagem_formatada = super().format(record)
        if record.meta:
            mensagem_formatada += f" {record.meta}"

        return mensagem_formatada

class AutomaticTracebackLogger(logging.Logger):
    """
    Logger personalizado com captura e formatação automática de stack traces para exceções.
    
    Características Principais:
    1. Captura Automática:
        - Detecta automaticamente exceções ativas
        - Inclui stack trace completo nos logs
        - Preserva contexto da exceção
    
    2. Níveis de Log Aprimorados:
        error(): 
            - Captura automática de exceções ativas
            - Ideal para erros recuperáveis
            - Mantém contexto do erro original
        
        exception():
            - Deve ser chamado dentro de blocos except
            - Sempre inclui stack trace completo
            - Formatação detalhada da exceção
        
        critical():
            - Para erros graves do sistema
            - Captura automática de exceções
            - Stack trace completo quando disponível
    
    3. Benefícios:
        - Reduz código boilerplate para logging de exceções
        - Melhora diagnóstico de problemas
        - Mantém consistência no formato dos logs
        - Facilita depuração posterior
    
    4. Integração:
        - Compatível com try/except
        - Suporte a contextos aninhados
        - Preserva hierarquia de exceções
    
    Exemplo de Uso:
        try:
            operacao_arriscada()
        except Exception:
            logger.exception("Falha na operação")  # Stack trace automático
        
        # Ou simplesmente:
        if erro_detectado:
            logger.error("Erro encontrado")  # Stack trace se houver exceção ativa
    """
    
    def error(self, msg, *args, **kwargs):
        exc_info = sys.exc_info()
        if exc_info[0] is not None:
            kwargs['exc_info'] = exc_info
        super().error(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        kwargs['exc_info'] = True
        self.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        exc_info = sys.exc_info()
        if exc_info[0] is not None:
            kwargs['exc_info'] = exc_info
        super().critical(msg, *args, **kwargs)

def _extract_call_chain(record) -> str:
    """
    Extrai call chain das funções do usuário, ignorando internas e threading.
    """
    chain = []
    for frame_info in inspect.stack():
        func = frame_info.function
        module = frame_info.frame.f_globals.get('__name__', '')
        filename = frame_info.filename
        # Ignora funções internas ou de módulos padrão
        if func in _INTERNAL_FUNCS:
            continue
        if module.startswith(('logging', 'inspect', 'colorama', 'threading')):
            continue
        if module == __name__:
            continue
        if not filename.endswith('.py'):
            continue
        chain.append(func)
    # Remove duplicatas e inverte ordem (raiz>atual)
    unique = []
    for f in reversed(chain):
        if not unique or unique[-1] != f:
            unique.append(f)
    return '>'.join(unique) or record.funcName

def _define_custom_levels():
    """
    Define níveis de log personalizados além dos níveis padrão do Python.
    
    Adiciona os seguintes níveis:
    - SUCCESS (25): Para registrar operações bem-sucedidas
    - SCREEN (35): Para registrar capturas de tela
    
    Os níveis são registrados no sistema de logging e métodos correspondentes
    são adicionados dinamicamente à classe Logger.
    """
    levels = {25: 'SUCCESS', 35: 'SCREEN'}
    for lvl, name in levels.items():
        if name not in logging._nameToLevel:
            logging.addLevelName(lvl, name)
            def log_for(self, msg, *args, _lvl=lvl, **kwargs):
                if self.isEnabledFor(_lvl):
                    self._log(_lvl, msg, args, **kwargs)
            setattr(Logger, name.lower(), log_for)

def _log_start(self: Logger, verbose: int = 1, timeout: float = 1.0):
    """
    Registra o início de um processo com informações detalhadas do ambiente.
    
    Args:
        verbose (int): Nível de detalhes a apresentar:
            0 = Apenas banner de início
            1 = Banner + sistema e ambiente (padrão)
            2 = Banner + sistema, ambiente e métricas iniciais
        timeout (float): Timeout em segundos para operações de rede (padrão: 1.0)
    """
    folder = Path(os.getcwd()).name
    script = Path(sys.argv[0]).name
    now = datetime.now()
    data = now.strftime('%d/%m/%Y')
    hora = now.strftime('%H:%M:%S')
    
    # Banner de início
    linhas = [
        "🚀 PROCESSO INICIADO",
        f"Data: {data} • Hora: {hora}",
        f"Script: {script} • Pasta: {folder}"
    ]
    banner = format_block("🚦INÍCIO", linhas)
    self.success(f"\n{banner}")
    
    # Reseta métricas para começar do zero (rápido e útil sempre)
    if verbose >= 1:
        self.reset_metrics()
    
    # Informações adicionais baseadas no nível verbose
    if verbose >= 1:
        # Registra o estado do sistema (operação leve)
        self.log_system_status()
        # Registra informações do ambiente (operação leve)
        self.log_environment()
    
    if verbose >= 2:
        # Snapshot de memória (pode ser pesado em sistemas grandes)
        self.debug("Registrando snapshot inicial de memória...")
        self.memory_snapshot()


def _log_end(self: Logger, verbose: int = 1, timeout: float = 1.0):
    """
    Registra o término de um processo com informações detalhadas.
    
    Args:
        verbose (int): Nível de detalhes a apresentar:
            0 = Apenas banner de fim
            1 = Banner + status do sistema (padrão)
            2 = Banner + status do sistema + relatório completo de métricas
        timeout (float): Timeout em segundos para operações de rede (padrão: 1.0)
    """
    folder = Path(os.getcwd()).name
    script = Path(sys.argv[0]).name
    now = datetime.now()
    data = now.strftime('%d/%m/%Y')
    hora = now.strftime('%H:%M:%S')
    
    # Informações adicionais baseadas no nível verbose
    if verbose >= 2:
        # Gera o relatório de métricas (operação leve)
        self.report_metrics()
        
        # Verifica vazamentos de memória (pode ser pesado em sistemas grandes)
        self.debug("Verificando possíveis vazamentos de memória...")
        self.check_memory_leak()
    
    if verbose >= 1:
        # Registra o estado final do sistema (operação leve)
        self.log_system_status()
    
    # Banner de finalização
    linhas = [
        "🏁 PROCESSO FINALIZADO",
        f"Data: {data} • Hora: {hora}",
        f"Script: {script} • Pasta: {folder}"
    ]
    banner = format_block("🏁 FIM", linhas)
    self.success(f"\n{banner}")

def _setup_directories(base_dir: Path, split_debug: bool):
    """
    Cria e configura a estrutura de diretórios necessária para o sistema de logging.
    
    Parâmetros:
        base_dir (Path): Diretório base onde os logs serão armazenados
        split_debug (bool): Se True, cria um diretório separado para logs de debug
    
    Cria os seguintes diretórios:
    - Logs: Diretório principal para todos os logs
    - LogsDEBUG: Diretório opcional para logs de debug (se split_debug=True)
    - PrintScreens: Diretório para armazenar capturas de tela
    
    Retorna:
        tuple: (screen_dir, debug_dir) - Paths para os diretórios criados
    """
    screen_dir = base_dir / 'PrintScreens'
    debug_dir  = base_dir / 'LogsDEBUG'
    base_dir.mkdir(parents=True, exist_ok=True)
    screen_dir.mkdir(parents=True, exist_ok=True)
    if split_debug:
        debug_dir.mkdir(parents=True, exist_ok=True)
    return screen_dir, debug_dir

def _get_log_filename(name: str) -> str:
    """
    Gera um nome de arquivo de log único com timestamp.
    
    Parâmetros:
        name (str): Nome base para o arquivo de log
    
    Retorna:
        str: Nome do arquivo no formato '<name> - DD-MM-YYYY HH-MM-SS.log'
             Se name não for fornecido, usa 'log' como padrão
    """
    ts = datetime.now().strftime('%d-%m-%Y %H-%M-%S')
    return f"{name or 'log'} - {ts}.log"

def _attach_screenshot(logger: Logger, name: str, screen_dir: Path, webdriver=None):
    """
    Captura e salva uma screenshot do sistema ou navegador.
    
    Parâmetros:
        logger (Logger): Instância do logger para registrar o processo
        name (str): Nome base para o arquivo de screenshot
        screen_dir (Path): Diretório onde as screenshots serão salvas
        webdriver (WebDriver, opcional): Instância do Selenium WebDriver para capturas do navegador
    
    Comportamento:
    - Tenta primeiro usar o webdriver se fornecido (para capturas do navegador)
    - Se não houver webdriver ou falhar, tenta usar pyautogui (para capturas do sistema)
    - Registra sucesso ou falha no log
    - Gera nome único com timestamp para cada arquivo
    """
    ts = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
    path = screen_dir / f"{name}_{ts}.png"
    if webdriver:
        try:
            webdriver.save_screenshot(str(path))
            logger.debug(f"Screenshot via webdriver salva em {path}")
        except:
            logger.warning(f"Falha ao capturar screenshot via webdriver: {path}")
    elif pyautogui:
        try:
            pyautogui.screenshot().save(path)
            logger.debug(f"Screenshot via pyautogui salva em {path}")
        except:
            logger.warning(f"Falha ao capturar screenshot via pyautogui: {path}")

class MetricsManager:
    """
    Gerenciador de métricas para rastreamento de tempo de execução e contadores.
    
    Características:
    - Rastreamento de tempo de execução de blocos de código
    - Contadores personalizados
    - Estatísticas de execução
    - Relatórios formatados
    """
    def __init__(self):
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.counters: Dict[str, int] = defaultdict(int)
        self._active_timers: Dict[str, float] = {}

    def add_execution_time(self, name: str, time_taken: float) -> None:
        """
        Adiciona um tempo de execução para uma métrica específica.
        
        Args:
            name: Nome da métrica
            time_taken: Tempo de execução em segundos
        """
        self.timers[name].append(time_taken)
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        """
        Incrementa um contador específico.
        
        Args:
            name: Nome do contador
            value: Valor a incrementar (padrão: 1)
        """
        self.counters[name] += value
    
    def get_statistics(self, name: str) -> Dict[str, float]:
        """
        Retorna estatísticas para uma métrica específica.
        
        Args:
            name: Nome da métrica
            
        Returns:
            Dicionário contendo estatísticas (count, total_time, average_time, min_time, max_time)
        """
        times = self.timers.get(name, [])
        if not times:
            return {}
        return {
            'count': len(times),
            'total_time': sum(times),
            'average_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times)
        }
    
    def get_counter(self, name: str) -> int:
        """
        Retorna o valor de um contador específico.
        
        Args:
            name: Nome do contador
            
        Returns:
            Valor atual do contador
        """
        return self.counters.get(name, 0)
    
    def reset(self) -> None:
        """
        Reseta todas as métricas.
        """
        self.timers.clear()
        self.counters.clear()
        self._active_timers.clear()

    def format_report(self) -> str:
        """
        Gera um relatório formatado com todas as métricas.
        
        Returns:
            Relatório formatado como string
        """
        lines = ['=== Relatório de Métricas ===']
        
        if self.timers:
            lines.append('\n--- Temporizadores ---')
            for name, times in self.timers.items():
                stats = self.get_statistics(name)
                lines.append(f"\n{name}:")
                lines.append(f"  Execuções: {stats['count']}")
                lines.append(f"  Tempo Total: {stats['total_time']:.3f}s")
                lines.append(f"  Média: {stats['average_time']:.3f}s")
                lines.append(f"  Min: {stats['min_time']:.3f}s")
                lines.append(f"  Max: {stats['max_time']:.3f}s")
        
        if self.counters:
            lines.append('\n--- Contadores ---')
            for name, value in self.counters.items():
                lines.append(f"{name}: {value}")
        
        return '\n'.join(lines)

# Funções de métricas para o logger
@contextmanager
def logger_timer(self: Logger, name: str, level: str = 'DEBUG') -> None:
    """
    Context manager para medir tempo de execução de um bloco de código.
    
    Args:
        name: Nome da métrica de tempo
        level: Nível de log para o resultado (padrão: DEBUG)
        
    Exemplo:
        with logger.timer('operacao_importante'):
            # código a ser medido
    """
    start_time = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start_time
        self._metrics.add_execution_time(name, elapsed)
        log_method = getattr(self, level.lower())
        log_method(f"[⏱️ {name}] Tempo de execução: {elapsed:.3f}s")

def logger_count(self: Logger, name: str, value: int = 1, level: str = 'DEBUG') -> None:
    """
    Incrementa um contador e registra no log.
    
    Args:
        name: Nome do contador
        value: Valor a incrementar (padrão: 1)
        level: Nível de log para o resultado (padrão: DEBUG)
    
    Exemplo:
        logger.count('eventos_processados')
    """
    self._metrics.increment_counter(name, value)
    log_method = getattr(self, level.lower())
    log_method(f"[📊 {name}] Contador: {self._metrics.get_counter(name)}")

def logger_report_metrics(self: Logger, level: str = 'INFO') -> None:
    """
    Gera e registra um relatório completo de métricas.
    
    Args:
        level: Nível de log para o relatório (padrão: INFO)
    
    Exemplo:
        logger.report_metrics()
    """
    # Obtém as métricas do gerenciador
    metrics = self._metrics
    log_method = getattr(self, level.lower())
    
    linhas = []
    
    # Formata os temporizadores
    if metrics.timers:
        linhas.append("⏱️ TEMPORIZADORES:")
        for name, times in metrics.timers.items():
            stats = metrics.get_statistics(name)
            linhas.append(f"  {name}:")
            linhas.append(f"    Execuções: {stats['count']} • Tempo total: {stats['total_time']:.3f}s")
            linhas.append(f"    Média: {stats['average_time']:.3f}s • Min: {stats['min_time']:.3f}s • Max: {stats['max_time']:.3f}s")
    
    # Formata os contadores
    if metrics.counters:
        if metrics.timers:  # Adiciona linha em branco se também tiver temporizadores
            linhas.append("")
        linhas.append("📊 CONTADORES:")
        for name, value in metrics.counters.items():
            linhas.append(f"  {name}: {value}")
    
    # Se não houver métricas, adiciona mensagem informativa
    if not metrics.timers and not metrics.counters:
        linhas.append("Nenhuma métrica registrada.")
    
    # Formata o bloco completo
    bloco = format_block("📊 RELATÓRIO DE MÉTRICAS", linhas)
    log_method(f"\n{bloco}")

def logger_reset_metrics(self: Logger) -> None:
    """
    Reseta todas as métricas acumuladas.
    
    Exemplo:
        logger.reset_metrics()
    """
    self._metrics.reset()
    self.debug("Métricas resetadas")

def _setup_metrics(logger: Logger) -> None:
    """
    Configura o sistema de métricas no logger.
    
    Args:
        logger: Instância do logger a ser configurada
    """
    metrics = MetricsManager()
    setattr(logger, '_metrics', metrics)
    
    # Adiciona os métodos ao logger
    setattr(Logger, 'timer', logger_timer)
    setattr(Logger, 'count', logger_count)
    setattr(Logger, 'report_metrics', logger_report_metrics)
    setattr(Logger, 'reset_metrics', logger_reset_metrics)

class SystemMonitor:
    """
    Monitor de recursos do sistema e memória.
    
    Características:
    - Monitoramento de uso de CPU
    - Monitoramento de memória
    - Contagem de objetos Python
    - Detecção de vazamentos de memória
    """
    def __init__(self):
        self.process = psutil.Process()
        self._baseline_memory: Optional[float] = None
        self._object_counts: Optional[Dict[str, int]] = None
    
    def get_memory_usage(self) -> Tuple[float, float]:
        """
        Retorna uso de memória (MB) do processo e do sistema.
        
        Returns:
            Tupla contendo (memória_do_processo_MB, percentual_de_memória_do_sistema)
        """
        process_memory = self.process.memory_info().rss / 1024 / 1024
        system_memory = psutil.virtual_memory().percent
        return process_memory, system_memory
    
    def get_cpu_usage(self) -> Tuple[float, float]:
        """
        Retorna uso de CPU (%) do processo e do sistema.
        
        Returns:
            Tupla contendo (cpu_do_processo_percentual, cpu_do_sistema_percentual)
        """
        process_cpu = self.process.cpu_percent()
        system_cpu = psutil.cpu_percent()
        return process_cpu, system_cpu
    
    def take_memory_snapshot(self) -> None:
        """
        Registra estado atual da memória como baseline.
        """
        gc.collect()
        self._baseline_memory = self.get_memory_usage()[0]
        self._object_counts = self._count_objects()
    
    def _count_objects(self) -> Dict[str, int]:
        """
        Conta objetos Python por tipo.
        
        Returns:
            Dicionário com contagem de objetos por tipo
        """
        return {str(type(obj).__name__): len([o for o in gc.get_objects() if type(o) is type(obj)])
                for obj in gc.get_objects()}
    
    def get_memory_diff(self) -> Tuple[float, Dict[str, int]]:
        """
        Retorna diferença de memória e objetos desde o último snapshot.
        
        Returns:
            Tupla contendo (diferença_de_memória_MB, dicionário_com_diferenças_de_objetos)
        """
        if self._baseline_memory is None:
            return 0.0, {}
        
        current_memory = self.get_memory_usage()[0]
        memory_diff = current_memory - self._baseline_memory
        
        current_counts = self._count_objects()
        object_diff = {
            name: current_counts.get(name, 0) - self._object_counts.get(name, 0)
            for name in set(current_counts) | set(self._object_counts or {})
            if current_counts.get(name, 0) != self._object_counts.get(name, 0)
        }
        
        return memory_diff, object_diff

def format_block(title: str, lines: List[str]) -> str:
    """
    Cria um bloco ASCII com título centralizado e linhas internas todas da mesma largura,
    medindo corretamente os emojis.
    """
    space = " "*36
    # 1. Prepara o título
    title_str = f"[{title}]"
    title_w = wcswidth(title_str)

    # 2. Calcula a largura máxima de qualquer linha de conteúdo
    content_ws = [wcswidth(line) for line in lines] if lines else [0]
    max_content_w = max(content_ws)

    # 3. Define a largura total do bloco (conteúdo + margens)
    inner_width = max(title_w, max_content_w)  # largura útil
    total_w = inner_width + 4  # +2 espaços e +2 bordas verticais

    # 4. Monta a linha de topo com título centralizado
    pad_total = total_w - title_w - 2  # -2 para os cantos ╭╮
    left = pad_total // 2
    right = pad_total - left
    topo = f"{space}╭{'─'*left}{title_str}{'─'*right}╮"

    # 5. Linhas internas todas com a MESMA largura (total_w)
    corpo = []
    for line, w in zip(lines, content_ws):
        # quantas colunas "vazias" faltam para chegar ao inner_width
        falta = inner_width - w
        corpo.append(f"{space}│ {line}{' '*falta} │")

    # 6. Base do bloco
    base = f"{space}╰{'─'*(total_w-2)}╯"

    return "\n".join([topo] + corpo + [base])

# Funções de monitoramento para o logger
def logger_log_system_status(self: Logger, level: str = 'INFO') -> None:
    proc_mem, sys_mem = self._monitor.get_memory_usage()
    proc_cpu, sys_cpu = self._monitor.get_cpu_usage()
    
    linhas = [
        f"💻 CPU: Processo {proc_cpu:.1f}% • Sistema: {sys_cpu:.1f}%",
        f"💾 Memória: {proc_mem:.1f}MB • Sistema: {sys_mem:.1f}%"
    ]
    bloco = format_block("🧠 STATUS DO SISTEMA", linhas)

    getattr(self, level.lower())(f"\n{bloco}")

def logger_memory_snapshot(self: Logger) -> None:
    """
    Registra snapshot da memória atual para comparação posterior.
    
    Exemplo:
        logger.memory_snapshot()
    """
    self._monitor.take_memory_snapshot()
    self.debug("Snapshot de memória registrado")

def logger_check_memory_leak(self: Logger, level: str = 'WARNING') -> None:
    """
    Verifica diferenças de memória desde o último snapshot.
    
    Args:
        level: Nível de log para avisos de vazamento (padrão: WARNING)
    
    Exemplo:
        logger.check_memory_leak()
    """
    memory_diff, object_diff = self._monitor.get_memory_diff()
    
    if not memory_diff and not object_diff:
        self.debug("Nenhum vazamento de memória detectado")
        return
    
    log_method = getattr(self, level.lower())
    message = [f"⚠️ Possível vazamento de memória detectado: {memory_diff:.1f}MB"]
    
    if object_diff:
        message.append("\nMudanças nos objetos:")
        for obj_type, diff in object_diff.items():
            if abs(diff) > 10:  # Reporta apenas diferenças significativas
                message.append(f"  {obj_type}: {diff:+d}")
    
    log_method('\n'.join(message))

def _setup_monitoring(logger: Logger) -> None:
    """
    Configura o sistema de monitoramento no logger.
    
    Args:
        logger: Instância do logger a ser configurada
    """
    monitor = SystemMonitor()
    setattr(logger, '_monitor', monitor)
    
    # Adiciona os métodos ao logger
    setattr(Logger, 'log_system_status', logger_log_system_status)
    setattr(Logger, 'memory_snapshot', logger_memory_snapshot)
    setattr(Logger, 'check_memory_leak', logger_check_memory_leak)

class ContextManager:
    """
    Gerenciador de contexto para logging hierárquico.
    Permite agrupar logs relacionados e criar uma hierarquia de execução.
    """
    def __init__(self):
        self._context_separator = ' → '
    
    def get_current_context(self) -> str:
        """Retorna o contexto atual formatado."""
        contexts = _log_context.get()
        return self._context_separator.join(contexts) if contexts else ''
    
    @contextmanager
    def context(self, name: str):
        """
        Context manager para adicionar contexto temporário aos logs.
        
        Exemplo:
            with logger.context_manager.context('Processamento'):
                logger.info('Iniciando...')  # Será logado com contexto
        """
        token = _log_context.set(_log_context.get() + [name])
        try:
            yield
        finally:
            _log_context.reset(token)

# Funções de contexto para o logger
def logger_context(self: Logger, name: str) -> contextmanager:
    """
    Adiciona contexto temporário aos logs.
        
    Exemplo:
        with logger.context('Operação'):
            logger.info('Processando...')  # Será logado como: [Operação] Processando...
    """
    @contextmanager
    def context_wrapper():
        with self._context_manager.context(name):
            yield
    return context_wrapper()

# Função para sobrescrever o método _log do logger para incluir informações de contexto
def log_with_context(self: Logger, level, msg, args, **kwargs):
    """
    Versão modificada do método _log que inclui informações de contexto.
    Substitui o método padrão do logger para adicionar o contexto atual às mensagens.
    """
    context = self._context_manager.get_current_context()
    if context:
        msg = f"[{context}] {msg}"
    self._original_log(level, msg, args, **kwargs)


class Profiler:
    """
    Gerenciador de profiling para análise de performance de código.
    Utiliza cProfile para coletar métricas detalhadas de execução.
    """
    def __init__(self):
        self.profiler = None
        self._active = False
    
    def start(self) -> None:
        """Inicia a coleta de métricas de profiling."""
        if not self._active:
            self.profiler = cProfile.Profile()
            self.profiler.enable()
            self._active = True
    
    def stop(self) -> str:
        """
        Para a coleta de métricas e retorna relatório formatado.
        
        Retorna:
            str: Relatório de profiling formatado
        """
        if not self._active:
            return "Profiler não está ativo"
        
        self.profiler.disable()
        self._active = False
        
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # Limita aos 20 itens mais relevantes
        return s.getvalue()


# Funções de profiling para o logger
@contextmanager
def logger_profile_cm(self: Logger, name: str = None) -> None:
    """
    Context manager para profiling de código.
    
    Args:
        name: Nome da seção a ser perfilada
        
    Exemplo:
        with logger.profile_cm('operacao'):
            # código a ser analisado
    """
    section_name = name or 'Seção'
    self.info(f"🔍 Iniciando profiling: {section_name}")
    self._profiler.start()
    try:
        yield
    finally:
        report = self._profiler.stop()
        self.info(f"📊 Resultado do profiling ({section_name}):\n{report}")

def logger_profile(self: Logger, func: Optional[Callable] = None, *, name: str = None) -> Any:
    """
    Decorator para profiling de código.
    
    Args:
        func: Função a ser decorada
        name: Nome opcional para o perfil
        
    Exemplo:
        @logger.profile
        def funcao_pesada():
            ...
    """
    if func is None:
        # Se chamado sem função, retorna o context manager diretamente
        return logger_profile_cm(self, name)
        
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with logger_profile_cm(self, func.__name__):
            return func(*args, **kwargs)
    return wrapper

def _setup_context_and_profiling(logger: Logger) -> None:
    """
    Configura rastreamento de contexto e profiling no logger.
    
    Args:
        logger: Instância do logger a ser configurada
    """
    # Inicializa os gerenciadores
    context_manager = ContextManager()
    profiler = Profiler()
    
    # Armazena os gerenciadores no logger
    setattr(logger, '_context_manager', context_manager)
    setattr(logger, '_profiler', profiler)
    
    # Guarda referência ao método _log original
    setattr(logger, '_original_log', logger._log)
    
    # Substitui o método _log
    setattr(Logger, '_log', log_with_context)
    
    # Adiciona os métodos ao logger
    setattr(Logger, 'context', logger_context)
    setattr(Logger, 'profile', logger_profile)
    setattr(Logger, 'profile_cm', logger_profile_cm)

class DependencyManager:
    """
    Gerenciador de informações sobre dependências e ambiente de execução.
    Coleta e formata informações sobre pacotes instalados e sistema.
    """
    def __init__(self):
        self._cached_info: Optional[Dict[str, Any]] = None
        self._last_update: float = 0
        self._cache_duration: int = 300  # 5 minutos
    
    def get_environment_info(self, force_update: bool = False) -> Dict[str, Any]:
        """
        Coleta informações sobre o ambiente de execução.
        
        Args:
            force_update: Se True, força atualização do cache
        
        Returns:
            Dicionário contendo informações sobre Python, sistema e pacotes
        """
        now = time.time()
        if self._cached_info and not force_update and (now - self._last_update) < self._cache_duration:
            return self._cached_info
        
        info = {
            'python': {
                'version': platform.python_version(),
                'implementation': platform.python_implementation(),
                'compiler': platform.python_compiler(),
                'build': platform.python_build(),
            },
            'system': {
                'os': platform.system(),
                'release': platform.release(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'node': platform.node(),
            },
            'packages': self._get_installed_packages()
        }
        
        self._cached_info = info
        self._last_update = now
        return info
    
    def _get_installed_packages(self) -> Dict[str, str]:
        """
        Retorna dicionário com pacotes instalados e suas versões.
        
        Returns:
            Dicionário com nome do pacote como chave e versão como valor
        """
        return {pkg.key: pkg.version for pkg in pkg_resources.working_set}

class NetworkMonitor:
    """
    Monitor de atividades de rede e métricas de conexão.
    Rastreia requisições HTTP, latência e erros de rede.
    """
    def __init__(self):
        self.metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_requests': 0,
            'total_errors': 0,
            'total_bytes': 0,
            'latencies': [],
        })
        self._executor = ThreadPoolExecutor(max_workers=5)
    
    def check_connection(self, host: str = "8.8.8.8", port: int = 53, timeout: float = 1.0) -> Tuple[bool, Optional[float]]:
        """
        Verifica conectividade com a internet.
        
        Args:
            host: Host para verificar conexão (padrão: servidor DNS do Google)
            port: Porta para conexão (padrão: 53)
            timeout: Tempo limite em segundos (padrão: 1.0)
            
        Returns:
            Tupla contendo (está_conectado, latência_em_ms)
        """
        try:
            start = time.time()
            socket.create_connection((host, port), timeout=timeout)
            return True, (time.time() - start) * 1000
        except OSError:
            return False, None
    
    def measure_latency(self, url: str, timeout: float = 1.0) -> Dict[str, Any]:
        """
        Mede latência para uma URL específica.
        
        Args:
            url: URL para medir latência
            timeout: Tempo limite em segundos (padrão: 1.0)
            
        Returns:
            Dicionário contendo métricas de latência ou erro
        """
        try:
            start = time.time()
            response = requests.get(url, timeout=timeout)
            latency = (time.time() - start) * 1000
            
            domain = urlparse(url).netloc
            metrics = self.metrics[domain]
            metrics['total_requests'] += 1
            metrics['latencies'].append(latency)
            metrics['total_bytes'] += len(response.content)
            
            if len(metrics['latencies']) > 100:
                metrics['latencies'] = metrics['latencies'][-100:]
            
            return {
                'latency': latency,
                'status_code': response.status_code,
                'content_size': len(response.content),
            }
        except requests.RequestException as e:
            domain = urlparse(url).netloc
            self.metrics[domain]['total_errors'] += 1
            return {
                'error': str(e),
                'type': type(e).__name__
            }

# Funções de dependências e rede para o logger
def logger_log_environment(self: Logger, level: str = 'INFO') -> None:
    """
    Registra informações detalhadas sobre o ambiente de execução.
    
    Args:
        level: Nível de log para as informações (padrão: INFO)
    
    Exemplo:
        logger.log_environment()
    """
    info = self._dep_manager.get_environment_info()
    log_method = getattr(self, level.lower())

    linhas = [
        f"Python {info['python']['version']} ({info['python']['implementation']})",
        f"SO: {info['system']['os']} {info['system']['release']} ({info['system']['machine']})",
        "Pacotes Principais:"
    ]

    important = ['requests', 'psutil', 'colorama', 'pyautogui']
    for pkg in important:
        if pkg in info['packages']:
            linhas.append(f"  - {pkg}: {info['packages'][pkg]}")

    bloco = format_block("🔧 AMBIENTE", linhas)
    log_method(f"\n{bloco}")

def logger_check_connectivity(self: Logger, url: str = None, level: str = 'INFO', timeout: float = 1.0) -> None:
    """
    Verifica e registra status da conectividade.
    
    Args:
        url: URL opcional para testar conectividade específica
        level: Nível de log para o resultado (padrão: INFO)
        timeout: Timeout em segundos para as verificações de rede (padrão: 1.0)
    
    Exemplo:
        logger.check_connectivity('https://api.exemplo.com')
    """
    # Verifica conexão básica com timeout reduzido
    connected, latency = self._net_monitor.check_connection(timeout=timeout)
    log_method = getattr(self, level.lower())

    linhas = []
    if connected:
        linhas.append(f"Status: ✅ Conectado • Latência: {latency:.1f}ms")
    else:
        linhas.append("❌ Sem conexão com a internet")

    if url:
        try:
            metrics = self._net_monitor.measure_latency(url, timeout=timeout)
            if 'latency' in metrics:
                linhas.append(f"URL Testada: {url}")
                linhas.append(f"↳ Latência: {metrics['latency']:.1f}ms • Status: {metrics['status_code']} • Tamanho: {metrics['content_size']/1024:.1f}KB")
            else:
                linhas.append(f"❌ Erro ao acessar {url}: {metrics['error']}")
        except Exception as e:
            linhas.append(f"❌ Erro ao testar {url}: {str(e)}")

    bloco = format_block("🌐 CONECTIVIDADE", linhas)
    log_method(f"\n{bloco}")

def logger_get_network_metrics(self: Logger, domain: str = None) -> Dict[str, Any]:
    """
    Retorna métricas de rede coletadas.
    
    Args:
        domain: Domínio específico para obter métricas (opcional)
    
    Returns:
        Dicionário contendo métricas de rede
    
    Exemplo:
        metrics = logger.get_network_metrics('api.exemplo.com')
    """
    if domain:
        metrics = self._net_monitor.metrics[domain]
        if metrics['latencies']:
            avg_latency = sum(metrics['latencies']) / len(metrics['latencies'])
            metrics['average_latency'] = avg_latency
        return metrics
    return dict(self._net_monitor.metrics)

def _setup_dependencies_and_network(logger: Logger) -> None:
    """
    Configura monitoramento de dependências e rede no logger.
    
    Args:
        logger: Instância do logger a ser configurada
    """
    dep_manager = DependencyManager()
    net_monitor = NetworkMonitor()
    
    setattr(logger, '_dep_manager', dep_manager)
    setattr(logger, '_net_monitor', net_monitor)
    
    # Adiciona os métodos ao logger
    setattr(Logger, 'log_environment', logger_log_environment)
    setattr(Logger, 'check_connectivity', logger_check_connectivity)
    setattr(Logger, 'get_network_metrics', logger_get_network_metrics)

def logger_sleep(self: Logger, duration: float, unit: str = 's', level: str = 'DEBUG', message: str = None) -> None:
    """
    Pausa a execução pelo tempo especificado e registra a pausa no log.
    
    Args:
        duration: Duração da pausa
        unit: Unidade de tempo ('s'=segundos, 'ms'=milissegundos, 'min'=minutos, 'h'=horas)
        level: Nível de log para as mensagens (padrão: DEBUG)
        message: Mensagem opcional para explicar a pausa
    
    Exemplo:
        logger.sleep(2.5)                # Espera 2.5 segundos
        logger.sleep(500, unit='ms')     # Espera 500 milissegundos
        logger.sleep(1, unit='min')      # Espera 1 minuto
        logger.sleep(2, message="Aguardando conexão")  # Com mensagem explicativa
    """
    # Converter para segundos com base na unidade
    seconds = duration
    unit_name = "segundo(s)"
    
    if unit == 'ms':
        seconds = duration / 1000
        unit_name = "milissegundo(s)"
    elif unit == 'min':
        seconds = duration * 60
        unit_name = "minuto(s)"
    elif unit == 'h':
        seconds = duration * 3600
        unit_name = "hora(s)"
    
    # Criar mensagem de log
    msg = message or f"Aguardando {duration} {unit_name}"
    log_method = getattr(self, level.lower())
    
    # Registrar início, fazer pausa e registrar fim
    log_method(f"⏳ {msg}")
    start = time.time()
    time.sleep(seconds)
    elapsed = time.time() - start
    # log_method(f"⌛ {msg} - concluído em {elapsed:.2f}s")
    
    return None

class LoggerProgressBar:
    """
    Barra de progresso integrada ao logger, inspirada na biblioteca tqdm.
    
    Características:
    - Exibe barra de progresso no console
    - Registra atualizações periódicas no log
    - Compatível com outras mensagens de log durante a operação
    - Funciona como iterador e context manager
    - Suporta atualizações manuais (método update)
    """
    def __init__(self, 
                 logger: Logger,
                 total: int = None,
                 desc: str = '',
                 leave: bool = True,
                 unit: str = 'it',
                 log_interval: float = 1.0,
                 log_level: str = 'INFO'):
        """
        Inicializa a barra de progresso.
        
        Args:
            logger: Instância do logger para registrar o progresso
            total: Total de iterações (opcional para context manager)
            desc: Descrição da operação
            leave: Se True, mantém a barra após completar
            unit: Unidade das iterações (ex: 'it', 'files', 'MB')
            log_interval: Intervalo mínimo (segundos) entre atualizações no log
            log_level: Nível de log para as mensagens de progresso
        """
        self.logger = logger
        self.total = total
        self.desc = desc
        self.leave = leave
        self.unit = unit
        self.log_interval = log_interval
        self.log_level = log_level
        
        # Estado interno
        self.n = 0
        self.start_time = time.time()
        self.last_log_time = self.start_time
        self.last_print_n = 0
        self.last_print_time = self.start_time
        self.closed = False
        self.display_threshold = 0.05  # Atualiza exibição após 5% de progresso
        self.last_line_len = 0  # Para rastrear o tamanho da última linha impressa
        self.bar_position = 0   # Para rastrear a posição da barra no console
        
        # Iniciar
        self._log_progress(initial=True)
    
    def update(self, n: int = 1) -> None:
        """
        Atualiza o progresso incrementando n unidades.
        
        Args:
            n: Número de unidades a incrementar
        """
        if self.closed:
            return
            
        self.n += n
        now = time.time()
        
        # Decide se deve atualizar o log (menos frequente)
        if (now - self.last_log_time >= self.log_interval or 
            self.n == self.total):
            self._log_progress()
            self.last_log_time = now
            # Garante que a barra seja redesenhada após enviar log
            self._print_progress()
            return
        
        # Atualiza a exibição no console com mais frequência, mas não a cada chamada
        # para evitar sobrecarga de E/S
        if self.n == self.total or now - self.last_print_time >= 0.2:  # Atualização a cada 200ms
            self._print_progress()
            self.last_print_time = now
    
    def close(self) -> None:
        """Finaliza a barra de progresso."""
        if not self.closed:
            self.closed = True
            self._log_progress(final=True)
            self._print_progress(final=True)

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self.closed:
            raise StopIteration
        return self
    
    def __call__(self, iterable):
        """
        Envolve um iterável para mostrar o progresso.
        
        Args:
            iterable: O iterável a ser processado
            
        Returns:
            Um iterador que atualiza a barra de progresso
        """
        # Tenta obter o comprimento do iterável se total não foi informado
        if self.total is None:
            try:
                self.total = len(iterable)
            except (TypeError, AttributeError):
                # Se não conseguir, tentamos converter para lista primeiro
                try:
                    iterable = list(iterable)
                    self.total = len(iterable)
                except:
                    # Se tudo falhar, não definimos o total
                    pass
                    
        # Adiciona uma mensagem inicial no log
        self._log_progress(initial=True)
        
        for obj in iterable:
            yield obj
            self.update(1)
        
        self.close()
    
    def _format_time(self, seconds: float) -> str:
        """Formata o tempo em uma string legível."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}min"
        else:
            return f"{seconds/3600:.1f}h"
    
    def _format_bar(self, pct: float, width: int = 20) -> str:
        """Cria uma barra de progresso visual."""
        filled = int(width * pct)
        bar = '█' * filled + '░' * (width - filled)
        return bar
    
    def _get_progress_info(self) -> dict:
        """Calcula e retorna informações sobre o progresso atual."""
        now = time.time()
        elapsed = now - self.start_time
        
        # Evita divisão por zero
        if self.total is None or self.total == 0:
            pct = 0
            rate = 0
            remaining = 0
        else:
            pct = self.n / self.total
            rate = self.n / elapsed if elapsed > 0 else 0
            remaining = (self.total - self.n) / rate if rate > 0 else 0
        
        return {
            'count': self.n,
            'total': self.total,
            'pct': pct * 100,
            'bar': self._format_bar(pct),
            'elapsed': elapsed,
            'elapsed_str': self._format_time(elapsed),
            'remaining': remaining,
            'remaining_str': self._format_time(remaining),
            'rate': rate,
            'rate_str': f"{rate:.1f} {self.unit}/s"
        }
    
    def _log_progress(self, initial: bool = False, final: bool = False) -> None:
        """Registra o progresso no log."""
        info = self._get_progress_info()
        
        if initial:
            message = f"⏱️ Iniciando: {self.desc} (0/{info['total']} {self.unit})"
        elif final:
            message = f"✅ Concluído: {self.desc} ({info['count']}/{info['total']} {self.unit}) em {info['elapsed_str']}"
        else:
            # Inclui a barra visual nos arquivos de log
            message = (f"📊 {self.desc}: [{info['bar']}] "
                      f"{info['count']}/{info['total']} {self.unit} "
                      f"({info['pct']:.1f}%) • Taxa: {info['rate_str']} "
                      f"• Restante: {info['remaining_str']}")
        
        log_method = getattr(self.logger, self.log_level.lower())
        log_method(message)
    
    def _print_progress(self, final: bool = False) -> None:
        """Atualiza a barra de progresso no console."""
        if not sys.stdout.isatty():
            return  # Não mostra barra interativa se não estiver em um terminal
        
        info = self._get_progress_info()
        
        # Limpa qualquer conteúdo na linha atual
        sys.stdout.write('\r' + ' ' * self.last_line_len + '\r')
        
        line = (f"{self.desc}: [{info['bar']}] "
               f"{info['count']}/{info['total']} "
               f"({info['pct']:.1f}%) {info['rate_str']} "
               f"• Restante: {info['remaining_str']}")
        
        # Limita o tamanho da linha
        max_len = 80
        if len(line) > max_len:
            line = line[:max_len-3] + "..."
            
        # Atualiza o tamanho da última linha
        self.last_line_len = len(line)
            
        sys.stdout.write(line)
        sys.stdout.flush()
        
        # Se for a linha final, adiciona uma quebra de linha
        if final and self.leave:
            sys.stdout.write('\n')
            sys.stdout.flush()


def logger_progress(self: Logger, 
                   iterable = None, 
                   total: int = None, 
                   desc: str = '', 
                   leave: bool = True,
                   unit: str = 'it',
                   log_interval: float = 1.0,
                   log_level: str = 'INFO') -> LoggerProgressBar:
    """
    Cria uma barra de progresso integrada ao logger.
    
    Pode ser usado de três formas:
    1. Como wrapper para um iterável:
       for item in logger.progress(items, desc="Processando"):
           process(item)
    
    2. Como context manager com total definido:
       with logger.progress(total=100, desc="Baixando") as pbar:
           for chunk in download_chunks():
               pbar.update(len(chunk))
    
    3. Para atualizações manuais:
       pbar = logger.progress(desc="Processando")
       pbar.update()
       pbar.close()
    
    Args:
        iterable: Iterável para processar (opcional)
        total: Total de iterações (necessário se não fornecer iterável)
        desc: Descrição da operação
        leave: Se True, mantém a barra após completar
        unit: Unidade das iterações (ex: 'it', 'files', 'MB')
        log_interval: Intervalo mínimo (segundos) entre registros no log
        log_level: Nível de log para mensagens de progresso
        
    Returns:
        Um objeto LoggerProgressBar
    """
    pbar = LoggerProgressBar(
        logger=self,
        total=total,
        desc=desc,
        leave=leave,
        unit=unit,
        log_interval=log_interval,
        log_level=log_level
    )
    
    if iterable is not None:
        return pbar(iterable)
    return pbar


class PrintCapture:
    """
    Captura chamadas à função print() e redireciona para o logger.
    
    Esta classe salva a função print() original e a substitui por uma versão
    que envia as mensagens para um logger específico.
    """
    def __init__(self):
        self.original_print = None
        self.logger = None
        self.log_level = 'INFO'
        self.prefix = ''
        self.active = False
    
    def start_capture(self, logger, level='WARNING', prefix='👉 Print(): '):
        """
        Inicia a captura de print(), redirecionando para o logger.
        
        Args:
            logger: Instância do logger para receber as mensagens
            level: Nível de log a usar (padrão: WARNING)
            prefix: Prefixo para adicionar às mensagens (para distinguir prints)
        """
        if self.active:
            return
            
        self.logger = logger
        self.log_level = level
        self.prefix = prefix
        self.active = True
        
        # Salva a função print original e substitui
        if self.original_print is None:
            self.original_print = builtins.print
        
        # Define a nova função print
        def new_print(*args, **kwargs):
            # Extrai parâmetros do print original
            file = kwargs.get('file', sys.stdout)
            sep = kwargs.get('sep', ' ')
            end = kwargs.get('end', '\n')
            flush = kwargs.get('flush', False)
            
            # Se o destino não é stdout, usa o print original
            if file is not sys.stdout:
                return self.original_print(*args, file=file, sep=sep, end=end, flush=flush)
            
            # Constrói a mensagem como o print faria
            message = sep.join(str(arg) for arg in args)
            
            # Envia para o logger
            log_method = getattr(self.logger, self.log_level.lower())
            log_method(f"-------------- ❌ Evite o Uso de Print ❌ --------------")
            log_method(f"{self.prefix}{message}")
            log_method(f"---------------------------------------------------------")

            # Se end não é newline, precisa imprimir mesmo assim para 
            # manter comportamento esperado em aplicações interativas
            if end != '\n':
                self.original_print(*args, sep=sep, end=end, flush=flush)
                
        # Substitui a função print global
        builtins.print = new_print
    
    def stop_capture(self):
        """Restaura a função print original."""
        if self.original_print and self.active:
            builtins.print = self.original_print
            self.active = False


# Instância global única
print_capture = PrintCapture()


def logger_capture_prints(self: Logger, active: bool = True, level: str = 'INFO', prefix: str = '👉 Print: '):
    """
    Ativa ou desativa a captura de print() para este logger.
    
    Quando ativada, todas as chamadas a print() serão redirecionadas para o logger.
    
    Args:
        active: Se True, ativa a captura; se False, restaura print() original
        level: Nível de log para as mensagens capturadas (padrão: INFO)
        prefix: Prefixo para adicionar às mensagens capturadas
        
    Exemplo:
        logger.capture_prints(True)   # Ativa captura
        print("Teste")                # Será registrado no logger
        logger.capture_prints(False)  # Desativa captura
    """
    if active:
        print_capture.start_capture(self, level=level, prefix=prefix)
    else:
        print_capture.stop_capture()


def _setup_utility_functions(logger: Logger) -> None:
    """
    Configura funções utilitárias no logger.
    
    Args:
        logger: Instância do logger a ser configurada
    """
    # Adiciona os métodos ao logger
    setattr(Logger, 'sleep', logger_sleep)
    setattr(Logger, 'progress', logger_progress)
    setattr(Logger, 'capture_prints', logger_capture_prints)
    
    # Importa builtins para a captura de print
    global builtins
    import builtins


def start_logger(name: str = None, log_dir: str = 'Logs', split_debug: bool = False, console_level: str = 'INFO', file_level: str = 'DEBUG') -> Logger:
    """
    Configura e inicializa um sistema de logging avançado com múltiplas funcionalidades.
    
    Args:
        name: Nome base para o logger e arquivos de log (opcional)
        log_dir: Diretório base para armazenar os logs (padrão: 'Logs')
        split_debug: Se True, separa logs de debug em arquivo próprio (padrão: False)
        console_level: Nível de log para o console (padrão: 'INFO')
        file_level: Nível de log para o arquivo (padrão: 'DEBUG')
    
    Returns:
        Logger: Instância configurada do logger com todos os recursos habilitados
    
    Exemplo:
        logger = start_logger('MeuApp')
        logger.start()
        logger.info('Iniciando processamento...')
        logger.end()
    """
    logger = _configure_base_logger(name, log_dir, split_debug, console_level, file_level)
    _setup_metrics(logger)
    _setup_monitoring(logger)
    _setup_context_and_profiling(logger)
    _setup_dependencies_and_network(logger)
    _setup_utility_functions(logger)
    return logger

def _configure_base_logger(name: str, log_dir: str, split_debug: bool, console_level: str = 'INFO', file_level: str = 'DEBUG') -> Logger:
    """
    Configura as funcionalidades base do logger.
    
    Args:
        name: Nome base para o logger e arquivos de log
        log_dir: Diretório base para armazenar os logs
        split_debug: Se True, separa logs de debug em arquivo próprio
        console_level: Nível de log para o console (padrão: 'INFO')
        file_level: Nível de log para o arquivo (padrão: 'DEBUG')
    
    Returns:
        Logger configurado com funcionalidades básicas
    """
    _init_colorama()
    _define_custom_levels()

    # Converte as strings de níveis para constantes do logging
    console_level_value = getattr(logging, console_level)
    file_level_value = getattr(logging, file_level)

    base = Path(log_dir)
    screen_dir, debug_dir = _setup_directories(base, split_debug)
    filename = _get_log_filename(name)

    logging.setLoggerClass(AutomaticTracebackLogger)
    logger = logging.getLogger(name)
    logger.setLevel(console_level_value)
    logger.handlers.clear()

    # Configuração dos handlers e formatters
    datefmt = '%Y-%m-%d %H:%M:%S'
    console_fmt = (
    "{asctime} {emoji} {levelname_color}{levelpad}- {message} {thread_disp}"
    )
    file_fmt = (
        "{asctime} {emoji} {levelname}{levelpad}- {message} <> "
        "     [{pathname}:{lineno}] - [Cadeia de Funcoes: {call_chain}📍] {thread_disp}"
    )

    # Console handler (colorido)
    ch = StreamHandler()
    ch.setFormatter(CustomFormatter(fmt=console_fmt, datefmt=datefmt, style='{'))
    logger.addHandler(ch)

    # File handlers (sem cores ANSI)
    formatter = Formatter(fmt=file_fmt, datefmt=datefmt, style='{')
    if split_debug:
        fh_dbg = FileHandler(debug_dir / filename, encoding='utf-8')
        fh_dbg.setLevel(logging.DEBUG)
        fh_dbg.setFormatter(formatter)
        logger.addHandler(fh_dbg)

        fh_info = FileHandler(base / filename, encoding='utf-8')
        fh_info.setLevel(logging.INFO)
        fh_info.setFormatter(formatter)
        logger.addHandler(fh_info)
    else:
        fh = FileHandler(base / filename, encoding='utf-8')
        fh.setLevel(file_level_value)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    
    # Métodos extras
    def _screen(self: Logger, msg: str, *args, webdriver=None, **kwargs) -> None:
        """
        Captura e registra uma screenshot com uma mensagem.
        
        Args:
            msg: Mensagem para registrar com a screenshot
            webdriver: Instância opcional do Selenium WebDriver
        """
        _attach_screenshot(self, name or 'log', screen_dir, webdriver)
        self.log(35, msg, *args, stacklevel=2, **kwargs)

    setattr(Logger, 'screen', _screen)
    setattr(Logger, 'start', _log_start)
    setattr(Logger, 'end', _log_end)

    # Armazena caminho do arquivo de log atual no logger
    file_path = base / filename
    setattr(logger, 'log_path', str(file_path))

    # Método cleanup para limpar o console
    def _cleanup(self: Logger) -> None:
        """Limpa o console."""
        cmd = 'cls' if os.name == 'nt' else 'clear'
        os.system(cmd)
    setattr(Logger, 'cleanup', _cleanup)

    # Método path para retornar o caminho do log atual
    def _path(self: Logger) -> str:
        """
        Retorna o caminho do arquivo de log atual.
        
        Returns:
            Caminho completo para o arquivo de log
        """
        return getattr(self, 'log_path', None)
    setattr(Logger, 'path', _path)

    # Método para pausar a execução com um input
    def _pause(self: Logger, msg: str = "Digite algo para continuar... ") -> str:
        """
        Pausa a execução e aguarda input do usuário.
        
        Args:
            msg: Mensagem a ser exibida (padrão: "Digite algo para continuar... ")
            
        Returns:
            Texto digitado pelo usuário
        """
        resp = input(msg)
        # registrando a resposta no log
        self.debug(f"Resposta do usuário: {resp}")
        return resp
    setattr(Logger, 'pause', _pause)

    return logger

def funcao3():
    logger.info("teste funcao 3")

def funcao2():
    logger.info("teste funcao 2")
    funcao3()

def funcao1():
    logger.info("teste funcao 1")
    funcao2()

if __name__ == '__main__':
    logger = start_logger("Exemplo", split_debug=True)

    # Inicia o logger com configurações padrão
    logger.start()

    with logger.context("Etapa A"):
        with logger.timer("tempo_total"):
            logger.info("🔍 Processando...")
            
            # Usando logger.sleep em vez de time.sleep
            logger.sleep(1.5, message="Processamento simulado")
            logger.count("eventos_lidos")

            # Exemplo 1: Usando progress como iterador
            logger.info("Iniciando processamento sequencial...")
            for i in logger.progress(range(100), desc="Iterando itens", unit="items"):
                logger.sleep(0.1, message=f"Processando item {i}")
                logger.count("eventos_lidos")
            
            # Exemplo 2: Usando progress como context manager
            logger.info("Iniciando download simulado...")
            with logger.progress(total=100, desc="Download", unit="MB") as pbar:
                for i in range(10):
                    # Simula download em partes
                    logger.sleep(0.2, message=f"Baixando parte {i+1}")
                    pbar.update(10)  # Atualiza 10MB por vez
                    
                    # Podemos ter outros logs durante o progresso
                    if i % 3 == 0:
                        logger.info(f"Verificando parte {i+1}")

            # Exemplo 3 : Metricas
            logger.report_metrics()

    # Ativa a captura de prints
    logger.capture_prints(True)
    print("Teste")

    print("Teste 2")
    print("Teste 3")        
    print("Teste 3")        
    print("Teste 3")        
    print("Teste 3")        
    print("Teste 3")        
    print("Teste 3")        
    print("Teste 3")        
    print("Teste 3")        
    logger.sleep(1)
    
    # Teste de conectividade com timeout curto
    logger.check_connectivity("https://google.com", timeout=0.5)

    funcao1()
    
    # Finaliza o logger
    logger.end()
