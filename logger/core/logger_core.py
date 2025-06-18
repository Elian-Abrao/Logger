import logging
from logging import Logger, Formatter, StreamHandler, FileHandler
from logger.handlers import ProgressStreamHandler
from pathlib import Path
from datetime import datetime
from colorama import init
import os
from logger.formatters.custom import CustomFormatter, AutomaticTracebackLogger, _define_custom_levels
import sys
from logger.core.context import _setup_context_and_profiling
from logger.extras.progress import format_block, logger_progress, combine_blocks
from logger.extras.network import _setup_dependencies_and_network
from logger.extras.printing import logger_capture_prints
import time
from contextlib import contextmanager
from typing import Optional, Dict, List, Tuple, Any, Callable
from collections import defaultdict
import psutil
import gc
import pkg_resources
import platform
import socket
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from wcwidth import wcswidth

try:
    import pyautogui
except Exception:
    pyautogui = None

# Inicializa o módulo colorama para permitir a exibição de cores no console do Windows.
# O parâmetro autoreset=True garante que as cores sejam resetadas automaticamente após cada uso.
def _init_colorama():
    init(autoreset=True)


def _log_start(self: Logger, verbose: int = 1, timeout: float = 1.0):
    """
    Registra o início de um processo com informações detalhadas do ambiente.
    
    Args:
        verbose (int): Nível de detalhes a apresentar:
            1 = Banner + sistema e ambiente (padrão)
            2 = Banner + sistema, ambiente e métricas iniciais
        timeout (float): Timeout em segundos para operações de rede (padrão: 1.0)
    """
    folder = Path(os.getcwd()).name
    script = Path(sys.argv[0]).name
    now = datetime.now()
    data = now.strftime('%d/%m/%Y')
    hora = now.strftime('%H:%M:%S')
    
    linhas = [
        "🚀 PROCESSO INICIADO",
        f"Data: {data} • Hora: {hora}",
        f"Script: {script} • Pasta: {folder}"
    ]
    banner = format_block("🚦INÍCIO", linhas)

    blocks = [banner]

    # Reseta métricas para começar do zero (rápido e útil sempre)
    if verbose >= 1:
        self.reset_metrics()
    
    # Informações adicionais baseadas no nível verbose
    if verbose >= 1:
        status_block = self.log_system_status(return_block=True)
        env_block = self.log_environment(return_block=True)
        blocks.extend([status_block, env_block])
    
    if verbose >= 2:
        # Snapshot de memória (pode ser pesado em sistemas grandes)
        self.debug("Registrando snapshot inicial de memória...")
        self.memory_snapshot()

    banner_final = combine_blocks(blocks)
    self.success(f"\n{banner_final}")


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
    
    blocks = []
    if verbose >= 1:
        status_block = self.log_system_status(return_block=True)
        blocks.append(status_block)
    
    # Banner de finalização
    linhas = [
        "🏁 PROCESSO FINALIZADO",
        f"Data: {data} • Hora: {hora}",
        f"Script: {script} • Pasta: {folder}"
    ]
    banner = format_block("🏁 FIM", linhas)
    blocks.insert(0, banner)
    banner_final = combine_blocks(blocks)
    self.success(f"\n{banner_final}")

def _setup_directories(base_dir: Path):
    """
    Cria e configura a estrutura de diretórios necessária para o sistema de logging.
    
    Parâmetros:
        base_dir (Path): Diretório base onde os logs serão armazenados
    
    Cria os seguintes diretórios:
    - Logs: Diretório principal para todos os logs
    - LogsDEBUG: Diretório para logs completos de depuração
    - PrintScreens: Diretório para armazenar capturas de tela
    
    Retorna:
        tuple: (screen_dir, debug_dir) - Paths para os diretórios criados
    """
    screen_dir = base_dir / 'PrintScreens'
    debug_dir  = base_dir / 'LogsDEBUG'
    base_dir.mkdir(parents=True, exist_ok=True)
    screen_dir.mkdir(parents=True, exist_ok=True)
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


# Funções de monitoramento para o logger
def logger_log_system_status(self: Logger, level: str = 'INFO', return_block: bool = False) -> str | None:
    proc_mem, sys_mem = self._monitor.get_memory_usage()
    proc_cpu, sys_cpu = self._monitor.get_cpu_usage()
    
    linhas = [
        f"💻 CPU: Processo {proc_cpu:.1f}% • Sistema: {sys_cpu:.1f}%",
        f"💾 Memória: {proc_mem:.1f}MB • Sistema: {sys_mem:.1f}%"
    ]
    bloco = format_block("🧠 STATUS DO SISTEMA", linhas)

    if return_block:
        return bloco

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
def logger_log_environment(self: Logger, level: str = 'INFO', return_block: bool = False) -> str | None:
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
    if return_block:
        return bloco
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

def _configure_base_logger(name: str, log_dir: str, console_level: str = 'INFO', file_level: str = 'DEBUG') -> Logger:
    """
    Configura as funcionalidades base do logger.
    
    Args:
        name: Nome base para o logger e arquivos de log
        log_dir: Diretório base para armazenar os logs

        console_level: Nível de log para o console (padrão: 'INFO')
        file_level: Nível de log para o arquivo (padrão: 'DEBUG')
        capture_prints: Habilita captura das chamadas ao print
        capture_prints: Habilita captura das chamadas ao print
    
    Returns:
        Logger configurado com funcionalidades básicas
    """
    _init_colorama()
    _define_custom_levels()

    # Converte as strings de níveis para constantes do logging
    console_level_value = getattr(logging, console_level)

    base = Path(log_dir)
    screen_dir, debug_dir = _setup_directories(base)
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
    ch = ProgressStreamHandler()
    ch.setFormatter(CustomFormatter(fmt=console_fmt, datefmt=datefmt, style='{'))
    logger.addHandler(ch)

    # File handlers (sem cores ANSI)
    formatter = Formatter(fmt=file_fmt, datefmt=datefmt, style='{')
    fh_dbg = FileHandler(debug_dir / filename, encoding='utf-8')
    fh_dbg.setLevel(logging.DEBUG)
    fh_dbg.setFormatter(formatter)
    logger.addHandler(fh_dbg)

    fh_info = FileHandler(base / filename, encoding='utf-8')
    fh_info.setLevel(logging.INFO)
    fh_info.setFormatter(formatter)
    logger.addHandler(fh_info)

    
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
    debug_path = debug_dir / filename
    setattr(logger, 'log_path', str(file_path))
    setattr(logger, 'debug_log_path', str(debug_path))

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

    def _debug_path(self: Logger) -> str:
        return getattr(self, 'debug_log_path', None)
    setattr(Logger, 'debug_path', _debug_path)


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
# Setup utility functions
def _setup_utility_functions(logger: Logger) -> None:
    setattr(Logger, "sleep", logger_sleep)
    setattr(Logger, "progress", logger_progress)
    setattr(Logger, "capture_prints", logger_capture_prints)

def start_logger(
    name: str = None,
    log_dir: str = 'Logs',
    console_level: str = 'INFO',
    file_level: str = 'DEBUG',
    capture_prints: bool = True,
) -> Logger:
    """
    Configura e inicializa um sistema de logging avançado com múltiplas funcionalidades.
    
    Args:
        name: Nome base para o logger e arquivos de log (opcional)
        log_dir: Diretório base para armazenar os logs (padrão: 'Logs')
        console_level: Nível de log para o console (padrão: 'INFO')
        file_level: Nível de log para o arquivo (padrão: 'DEBUG')
        capture_prints: Habilita captura das chamadas ao print
    
    Returns:
        Logger: Instância configurada do logger com todos os recursos habilitados
    
    Exemplo:
        logger = start_logger('MeuApp')
        logger.start()
        logger.info('Iniciando processamento...')
        logger.end()
    """
    logger = _configure_base_logger(name, log_dir, console_level, file_level)
    _setup_metrics(logger)
    _setup_monitoring(logger)
    _setup_context_and_profiling(logger)
    _setup_dependencies_and_network(logger)
    _setup_utility_functions(logger)
    if capture_prints:
        logger.capture_prints(True)
    return logger

def _configure_base_logger(name: str, log_dir: str, console_level: str = 'INFO', file_level: str = 'DEBUG') -> Logger:
    """
    Configura as funcionalidades base do logger.
    
    Args:
        name: Nome base para o logger e arquivos de log
        log_dir: Diretório base para armazenar os logs
        console_level: Nível de log para o console (padrão: 'INFO')
        file_level: Nível de log para o arquivo (padrão: 'DEBUG')
    
    Returns:
        Logger configurado com funcionalidades básicas
    """
    _init_colorama()
    _define_custom_levels()

    # Converte as strings de níveis para constantes do logging
    console_level_value = getattr(logging, console_level)

    base = Path(log_dir)
    screen_dir, debug_dir = _setup_directories(base)
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
    ch = ProgressStreamHandler()
    ch.setFormatter(CustomFormatter(fmt=console_fmt, datefmt=datefmt, style='{'))
    logger.addHandler(ch)

    # File handlers (sem cores ANSI)
    formatter = Formatter(fmt=file_fmt, datefmt=datefmt, style='{')
    fh_dbg = FileHandler(debug_dir / filename, encoding='utf-8')
    fh_dbg.setLevel(logging.DEBUG)
    fh_dbg.setFormatter(formatter)
    logger.addHandler(fh_dbg)

    fh_info = FileHandler(base / filename, encoding='utf-8')
    fh_info.setLevel(logging.INFO)
    fh_info.setFormatter(formatter)
    logger.addHandler(fh_info)

    
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
    debug_path = debug_dir / filename
    setattr(logger, 'log_path', str(file_path))
    setattr(logger, 'debug_log_path', str(debug_path))

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
    def _debug_path(self: Logger) -> str:
        return getattr(self, 'debug_log_path', None)
    setattr(Logger, 'debug_path', _debug_path)

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
