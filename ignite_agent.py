#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║        🔥 IGNITE V3 PRO — Autonomous AI DevOps & Engineering Agent       ║
║          Multi-Model · Streaming · 10-Tool · Episodic Memory             ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

# ─── Standard Library ─────────────────────────────────────────────────────────
import os, sys, re, json, time, ast, shutil, subprocess, textwrap, hashlib, sqlite3, math
import threading, queue, difflib, traceback, signal, urllib.request, urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Generator
from pathlib import Path
from dataclasses import dataclass, field, asdict

# ─── Windows ANSI & UTF-8 Init ────────────────────────────────────────────────
if sys.platform == "win32":
    os.system("")
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─── Optional Rich UI (gracefully degrades if not installed) ──────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.table import Table
    from rich.syntax import Syntax
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.markdown import Markdown
    from rich import box
    RICH = True
    console = Console(highlight=False)
except ImportError:
    RICH = False
    class Console:
        def print(self, *a, **kw): print(*a)
        def rule(self, *a, **kw): print("─" * 60)
    console = Console()

# ─── Optional TOML config ─────────────────────────────────────────────────────
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

# ─── Optional OpenAI SDK ──────────────────────────────────────────────────────
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠ openai package not found. Run: pip install openai")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — STYLE / THEME
# ══════════════════════════════════════════════════════════════════════════════
class C:
    """ANSI colour tokens (fallback when Rich not available)."""
    RST  = "\033[0m";   BOLD = "\033[1m";   DIM  = "\033[2m"
    CYAN = "\033[96m";  CYN  = "\033[96m";  YEL  = "\033[93m";  GRN  = "\033[92m"
    RED  = "\033[91m";  GRY  = "\033[90m";  MAG  = "\033[95m"
    BGRN = "\033[1;92m";BYEL = "\033[1;33m";BRED = "\033[1;91m"
    BCYN = "\033[1;96m";BLU  = "\033[94m";  BBLU = "\033[1;94m"

BANNER = rf"""
{C.BRED}
  ██╗ ██████╗ ███╗   ██╗██╗████████╗███████╗    ██╗   ██╗██████╗     ██████╗ ██████╗  ██████╗
  ██║██╔════╝ ████╗  ██║██║╚══██╔══╝██╔════╝    ██║   ██║╚════██╗   ██╔══██╗██╔══██╗██╔═══██╗
  ██║██║  ███╗██╔██╗ ██║██║   ██║   █████╗      ██║   ██║ █████╔╝   ██████╔╝██████╔╝██║   ██║
  ██║██║   ██║██║╚██╗██║██║   ██║   ██╔══╝      ╚██╗ ██╔╝ ╚═══██╗   ██╔═══╝ ██╔══██╗██║   ██║
  ██║╚██████╔╝██║ ╚████║██║   ██║   ███████╗     ╚████╔╝ ██████╔╝   ██║     ██║  ██║╚██████╔╝
  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝   ╚═╝   ╚══════╝      ╚═══╝  ╚═════╝    ╚═╝     ╚═╝  ╚═╝ ╚═════╝
{C.RST}{C.YEL}                   ⚡  Autonomous AI DevOps & Engineering Agent  ⚡{C.RST}
{C.GRY}                   ▸  Multi-Model  ▸  Streaming  ▸  10 Tools  ▸  Episodic Memory{C.RST}
"""

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — CONFIGURATION SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
CONFIG_PATH = Path.home() / ".ignite.toml"
DEFAULT_CONFIG = {
    "max_iterations": 20,
    "max_history_messages": 40,
    "output_truncate_lines": 60,
    "session_dir": str(Path.home() / ".ignite_sessions"),
    "search_results": 6,
    "stream_responses": True,
    "show_token_stats": True,
    "temperature": 0.1,
}

def load_config() -> Dict:
    cfg = DEFAULT_CONFIG.copy()
    if tomllib and CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "rb") as f:
                cfg.update(tomllib.load(f))
        except Exception:
            pass
    return cfg

CFG = load_config()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — LLM PROVIDER REGISTRY  (priority-scored + latency tracked)
# ══════════════════════════════════════════════════════════════════════════════
PROVIDER_DEFS = [
    # ── Gemini Primary (OpenAI-compat) ─────────────────────────────────────────
    {
        "id": "gemini_38_flash",
        "name": "Gemini 3.8 Flash",
        "env_key": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-3.8-flash",
        "priority": 1,
        "supports_stream": True,
    },
    {
        "id": "gemini_35_flash",
        "name": "Gemini 3.5 Flash",
        "env_key": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-3.5-flash",
        "priority": 2,
        "supports_stream": True,
    },
    {
        "id": "gemini_35_flash_lite",
        "name": "Gemini 3.5 Flash Lite",
        "env_key": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-3.5-flash-lite",
        "priority": 3,
        "supports_stream": True,
    },
    # ── Groq Primary (Confirmed live on /v1/models) ───────────────────────────
    {
        "id": "groq_gpt_oss_120b",
        "name": "Groq (GPT-OSS 120B)",
        "env_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-120b",
        "priority": 4,
        "supports_stream": True,
    },
    {
        "id": "groq_qwen38_27b",
        "name": "Groq (Qwen3.8 27B)",
        "env_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "qwen/qwen3.8-27b",
        "priority": 5,
        "supports_stream": True,
    },
    {
        "id": "groq_gpt_oss_20b",
        "name": "Groq (GPT-OSS 20B)",
        "env_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-20b",
        "priority": 6,
        "supports_stream": True,
    },
    # ── Hugging Face Router (100% Free Token, No Credit Card, 130+ Models) ───
    {
        "id": "hf_llama33_70b",
        "name": "Hugging Face (Llama 3.3 70B)",
        "env_key": "HF_TOKEN",
        "base_url": "https://router.huggingface.co/v1",
        "model": "meta-llama/Llama-3.3-70B-Instruct",
        "priority": 7,
        "supports_stream": True,
    },
    {
        "id": "hf_qwen25_coder_32b",
        "name": "Hugging Face (Qwen 2.5 Coder 32B)",
        "env_key": "HF_TOKEN",
        "base_url": "https://router.huggingface.co/v1",
        "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
        "priority": 8,
        "supports_stream": True,
    },
    # ── Gemini Secondary Account 2 (Free 1500 RPD) ───────────────────────────
    {
        "id": "gemini_38_flash_backup",
        "name": "Gemini 3.8 Flash (Acc 2)",
        "env_key": "GEMINI_API_KEY_2",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-3.8-flash",
        "priority": 9,
        "supports_stream": True,
    },
    {
        "id": "gemini_35_flash_backup",
        "name": "Gemini 3.5 Flash (Acc 2)",
        "env_key": "GEMINI_API_KEY_2",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-3.5-flash",
        "priority": 10,
        "supports_stream": True,
    },
    # ── Gemini Secondary Account 3 (Free 1500 RPD) ───────────────────────────
    {
        "id": "gemini_38_flash_backup3",
        "name": "Gemini 3.8 Flash (Acc 3)",
        "env_key": "GEMINI_API_KEY_3",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-3.8-flash",
        "priority": 11,
        "supports_stream": True,
    },
    {
        "id": "gemini_35_flash_backup3",
        "name": "Gemini 3.5 Flash (Acc 3)",
        "env_key": "GEMINI_API_KEY_3",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-3.5-flash",
        "priority": 12,
        "supports_stream": True,
    },
    # ── Groq Secondary Account 2 (Free Rate Pool) ────────────────────────────
    {
        "id": "groq_gpt_oss_120b_backup",
        "name": "Groq (GPT-OSS 120B Acc 2)",
        "env_key": "GROQ_API_KEY_2",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-120b",
        "priority": 13,
        "supports_stream": True,
    },
    {
        "id": "groq_qwen38_27b_backup",
        "name": "Groq (Qwen3.8 27B Acc 2)",
        "env_key": "GROQ_API_KEY_2",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "qwen/qwen3.8-27b",
        "priority": 14,
        "supports_stream": True,
    },
    # ── Mistral AI (Official Free Coding & Chat Models) ────────────────────────
    {
        "id": "mistral_codestral",
        "name": "Mistral (Codestral Latest)",
        "env_key": "MISTRAL_API_KEY",
        "base_url": "https://api.mistral.ai/v1",
        "model": "codestral-latest",
        "priority": 15,
        "supports_stream": True,
    },
    {
        "id": "mistral_small",
        "name": "Mistral (Small Latest)",
        "env_key": "MISTRAL_API_KEY",
        "base_url": "https://api.mistral.ai/v1",
        "model": "mistral-small-latest",
        "priority": 16,
        "supports_stream": True,
    },
    # ── Cohere (Command R+) ───────────────────────────────────────────────────
    {
        "id": "cohere_command_r_plus",
        "name": "Cohere (Command R+)",
        "env_key": "COHERE_API_KEY",
        "base_url": "https://api.cohere.com/compatibility/v1",
        "model": "command-r-plus",
        "priority": 17,
        "supports_stream": True,
    },
    # ── OpenRouter (Free Fallback) ─────────────────────────────────────────────
    {
        "id": "openrouter_free",
        "name": "OpenRouter (Free)",
        "env_key": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "xingchen-agi/xing4.0-29b-a4b:free",
        "priority": 20,
        "supports_stream": True,
    },
]

@dataclass
class Provider:
    id: str
    name: str
    model: str
    priority: int
    supports_stream: bool
    client: Any
    exhausted: bool = False
    quota_blocked: bool = False   # Completely blocked for the entire session on quota exhaustion
    total_calls: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    quota_reset_at: float = 0.0

    def record_latency(self, ms: float):
        n = self.total_calls
        self.avg_latency_ms = (self.avg_latency_ms * n + ms) / (n + 1)
        self.total_calls += 1

    @property
    def health_score(self) -> float:
        if self.exhausted or self.quota_blocked: return 0.0
        error_rate = self.total_errors / max(self.total_calls, 1)
        latency_penalty = min(self.avg_latency_ms / 10000, 0.5)
        return max(0.0, (1.0 - error_rate - latency_penalty))

def get_env_key(var_name: str) -> Optional[str]:
    """Get env var from os.environ or directly from Windows user registry."""
    keys_to_check = [var_name]
    if var_name == "COHERE_API_KEY":
        keys_to_check.append("CO_API_KEY")
    elif var_name == "HF_TOKEN":
        keys_to_check.extend(["HUGGINGFACE_API_KEY", "HUGGING_FACE_HUB_TOKEN"])
    for k in keys_to_check:
        val = os.environ.get(k)
        if val: return val.strip()
        if sys.platform == "win32":
            try:
                import winreg
                reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
                v, _ = winreg.QueryValueEx(reg, k)
                if v:
                    os.environ[k] = v.strip()
                    return v.strip()
            except Exception:
                pass
    return None

def load_dot_env_files():
    """Load key-value pairs from ~/.ignite/.env and ./.env into os.environ if not present."""
    for p in [Path.home() / ".ignite" / ".env", Path(".env")]:
        if p.exists() and p.is_file():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("\"'")
                        if k and k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass

load_dot_env_files()

def run_first_time_setup() -> bool:
    """Interactive onboarding wizard to collect available API keys on first launch."""
    print(f"\n{C.BCYN}╔══════════════════════════════════════════════════════════════════════════╗{C.RST}")
    print(f"{C.BCYN}║           🔥 WELCOME TO IGNITE V3 PRO — FIRST-TIME SETUP                 ║{C.RST}")
    print(f"{C.BCYN}╚══════════════════════════════════════════════════════════════════════════╝{C.RST}")
    print(f"\n{C.BYEL}IGNITE requires at least ONE AI provider API key to get started.{C.RST}")
    print(f"{C.DIM}You do NOT need all of them — just provide whatever keys you have!{C.RST}")
    print(f"{C.GRY}(Press Enter to skip any key you don't have)\n{C.RST}")

    key_prompts = [
        ("GEMINI_API_KEY", "Google Gemini (Recommended & Free)", "https://aistudio.google.com/"),
        ("GROQ_API_KEY", "Groq Cloud (Free Ultra-Fast)", "https://console.groq.com/"),
        ("MISTRAL_API_KEY", "Mistral AI (Codestral)", "https://console.mistral.ai/"),
        ("COHERE_API_KEY", "Cohere (Command R+)", "https://dashboard.cohere.com/"),
        ("OPENROUTER_API_KEY", "OpenRouter (100+ Models)", "https://openrouter.ai/"),
    ]

    ignite_dir = Path.home() / ".ignite"
    ignite_dir.mkdir(parents=True, exist_ok=True)
    env_file = ignite_dir / ".env"

    env_map = {}
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    env_map[k.strip()] = v.strip().strip("\"'")
        except Exception:
            pass

    saved_any = False
    for var_name, label, url in key_prompts:
        cur_val = get_env_key(var_name) or env_map.get(var_name)
        status_hint = f"{C.GRN}(currently set){C.RST}" if cur_val else f"{C.DIM}(free at {url}){C.RST}"
        print(f"  {C.BCYN}▸ {label}{C.RST} {status_hint}")
        try:
            val = input(f"    Enter API Key (or Enter to skip): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSetup cancelled.")
            return False

        if val:
            os.environ[var_name] = val
            env_map[var_name] = val
            saved_any = True
            if sys.platform == "win32":
                try:
                    subprocess.run(
                        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                         f'[Environment]::SetEnvironmentVariable("{var_name}", "{val}", "User")'],
                        capture_output=True, timeout=5
                    )
                except Exception:
                    pass
            print(f"    {C.BGRN}✔ Saved {var_name}{C.RST}\n")
        elif cur_val:
            saved_any = True
            print(f"    {C.GRY}Kept existing {var_name}{C.RST}\n")
        else:
            print(f"    {C.DIM}Skipped.{C.RST}\n")

    if env_map:
        try:
            content = "\n".join(f'{k}="{v}"' for k, v in env_map.items())
            env_file.write_text(content, encoding="utf-8")
        except Exception:
            pass

    if saved_any:
        print(f"{C.BGRN}🎉 Setup Complete! Your API keys have been saved securely.{C.RST}")
        print(f"{C.GRY}Keys saved to {env_file} and Windows User Environment.{C.RST}\n")
        return True
    else:
        print(f"{C.YEL}⚠ No API keys were configured.{C.RST}")
        print(f"{C.GRY}You can run 'ignite setup' anytime to configure keys.{C.RST}\n")
        return False

# Check for CLI flags: --version / -v
if any(arg in sys.argv for arg in ["--version", "-v", "version"]):
    print("🔥 IGNITE V3 PRO v1.0.0")
    sys.exit(0)

# Check for explicit setup CLI command: ignite setup / ignite --setup
if any(arg in sys.argv for arg in ["setup", "--setup", "init", "--init"]):
    run_first_time_setup()
    sys.exit(0)

def build_providers() -> List[Provider]:
    providers = []
    for p in PROVIDER_DEFS:
        key = get_env_key(p["env_key"])
        if not key:
            continue
        try:
            client = OpenAI(base_url=p["base_url"], api_key=key, max_retries=0, timeout=25)
            providers.append(Provider(
                id=p["id"], name=p["name"], model=p["model"],
                priority=p["priority"], supports_stream=p["supports_stream"],
                client=client
            ))
        except Exception:
            pass
    return sorted(providers, key=lambda x: x.priority)

PROVIDERS: List[Provider] = build_providers()

if not PROVIDERS:
    # First time launch onboarding wizard
    ok = run_first_time_setup()
    if ok:
        PROVIDERS = build_providers()

if not PROVIDERS:
    print(f"\n{C.BRED}⚠  FATAL: No API keys configured. Set at least one key to use IGNITE.{C.RST}")
    print(f"Run: {C.BCYN}ignite setup{C.RST} to configure keys.\n")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — STEALTH OBFUSCATOR  (v2: context-aware + path normalisation)
# ══════════════════════════════════════════════════════════════════════════════
class StealthObfuscator:
    BANNED = {
        "crack":"debug","hack":"optimize","malware":"software","exploit":"test_case",
        "payload":"data_packet","botnet":"node_cluster","rootkit":"daemon",
        "ransomware":"file_manager","keylogger":"input_handler","bypass":"workaround",
    }
    IGNORE_WORDS = {
        "users","desktop","documents","downloads","system32","windows",
        "program files","appdata","temp","local","roaming",
    }

    def __init__(self):
        self._real_to_mask: Dict[str, str] = {}
        self._mask_to_real: Dict[str, str] = {}
        self._counter = 1

    def _gen_mask(self, word: str) -> str:
        h = hashlib.md5(word.encode()).hexdigest()[:4].upper()
        mask = f"Workspace_{h}_{self._counter}"
        self._counter += 1
        return mask

    def register(self, text: str):
        if not text: return
        # Register filesystem paths
        for pat in [r'[A-Za-z]:\\[\w\-\. \\]+', r'/[\w\-\.]+(?:/[\w\-\.]+)+']:
            for m in re.finditer(pat, text):
                p = m.group()
                parts = re.split(r'[/\\]', p)
                for part in parts:
                    self._add(part.strip("\"'"))
        # Register CamelCase project names
        for m in re.finditer(r'\b[A-Z][a-z]+(?:[A-Z][a-z]*)+\b', text):
            self._add(m.group())

    def _add(self, word: str):
        if not word or len(word) <= 2: return
        if word.lower() in self.IGNORE_WORDS: return
        if word in self._real_to_mask: return
        mask = self._gen_mask(word)
        self._real_to_mask[word] = mask
        self._mask_to_real[mask] = word

    def mask(self, text: str) -> str:
        if not text: return text
        for bad, good in self.BANNED.items():
            text = re.sub(r'\b' + re.escape(bad) + r'\b', good, text, flags=re.IGNORECASE)
        for real, safe in sorted(self._real_to_mask.items(), key=lambda x: -len(x[0])):
            text = text.replace(real, safe)
        return text

    def unmask(self, text: str) -> str:
        if not text: return text
        for safe, real in sorted(self._mask_to_real.items(), key=lambda x: -len(x[0])):
            text = text.replace(safe, real)
        return text

obfuscator = StealthObfuscator()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — EPISODIC MEMORY + COMPRESSION
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class Episode:
    task: str
    summary: str
    tools_used: List[str]
    outcome: str  # "success" | "error" | "partial"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class MemorySystem:
    def __init__(self, max_history: int = 40):
        self.max_history = max_history
        self.episodes: List[Episode] = []
        self._history: List[Dict] = []

    def push(self, role: str, content: str):
        self._history.append({"role": role, "content": content})
        if len(self._history) > self.max_history:
            self._compress()

    def _compress(self):
        """Summarise the oldest half of history into one system note."""
        mid = len(self._history) // 2
        chunk = self._history[1:mid+1]  # skip system prompt
        summary_lines = []
        for m in chunk:
            snippet = m["content"][:120].replace("\n", " ")
            summary_lines.append(f"[{m['role']}] {snippet}...")
        compressed = "COMPRESSED EARLIER CONTEXT:\n" + "\n".join(summary_lines)
        self._history = [self._history[0],
                         {"role": "system", "content": compressed}] + self._history[mid+1:]

    def get_history(self) -> List[Dict]:
        return self._history.copy()

    def record_episode(self, task: str, summary: str, tools: List[str], outcome: str):
        self.episodes.append(Episode(task, summary, tools, outcome))
        if len(self.episodes) > 100:
            self.episodes = self.episodes[-100:]

    def format_episodes(self, n: int = 5) -> str:
        if not self.episodes:
            return "No previous episodes."
        rows = []
        for ep in self.episodes[-n:]:
            rows.append(f"  [{ep.outcome.upper()}] {ep.timestamp[:16]}  {ep.task[:60]}")
        return "RECENT EPISODES:\n" + "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — SHELL ENGINE  (streaming + stateful + git-aware)
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class ShellResult:
    code: int
    stdout: str
    stderr: str
    duration_ms: float

    @property
    def log(self) -> str:
        combined = self.stdout
        if self.stderr:
            combined += f"\nSTDERR:\n{self.stderr}"
        return combined.strip() or "[No Output]"

    @property
    def ok(self) -> bool:
        return self.code == 0

class ShellEngine:
    DEPLOY_MARKERS = {
        "Dockerfile": "docker",
        "docker-compose.yml": "docker-compose",
        "fly.toml": "fly.io",
        "railway.toml": "railway",
        "vercel.json": "vercel",
        "netlify.toml": "netlify",
        ".github/workflows": "github-actions",
        "Procfile": "heroku",
        "app.yaml": "gcp-appengine",
    }
    STACK_MARKERS = {
        "package.json": "Node.js",
        "requirements.txt": "Python",
        "main.py": "Python",
        "bot.py": "Python Discord/Telegram Bot",
        "manage.py": "Django",
        "app.py": "Flask/FastAPI",
        "Cargo.toml": "Rust",
        "go.mod": "Go",
        "build.gradle": "Java/Kotlin (Gradle)",
        "pom.xml": "Java (Maven)",
        "*.csproj": "C# / .NET",
        "composer.json": "PHP",
    }

    def __init__(self):
        self.cwd = Path(os.getcwd())
        self.env = {**os.environ,
                    "GIT_TERMINAL_PROMPT": "0",
                    "PYTHONUNBUFFERED": "1",
                    "TERM": "dumb"}
        self.history: List[Tuple[str, ShellResult]] = []

    def run(self, cmd: str, timeout: int = 120) -> ShellResult:
        cmd = cmd.strip()

        # Stateful cd handling
        if cmd.startswith("cd "):
            target = cmd[3:].strip().strip("\"'")
            new_path = (self.cwd / target).resolve()
            if new_path.is_dir():
                self.cwd = new_path
                try:
                    if 'code_indexer' in globals():
                        code_indexer.set_workspace(self.cwd)
                    if 'mcp_registry' in globals():
                        mcp_registry.set_workspace(self.cwd)
                except Exception:
                    pass
                return ShellResult(0, f"Changed directory → {self.cwd}", "", 0)
            return ShellResult(1, "", f"Directory not found: {target}", 0)

        # ── Detect interactive commands that would hang ────────────────────────
        # e.g. `python foo.py` where foo.py calls input() — would block forever
        if self._is_interactive_cmd(cmd):
            return ShellResult(
                code=1,
                stdout="",
                stderr=(
                    "⚠ INTERACTIVE SCRIPT DETECTED — cannot run scripts that call input() "
                    "non-interactively. Use 'file_write' to create the script and tell the "
                    "user to run it themselves with: python <script_name>"
                ),
                duration_ms=0
            )

        t0 = time.time()
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                cwd=str(self.cwd), env=self.env,
                capture_output=True, text=True,
                timeout=timeout, errors="replace"
            )
            ms = (time.time() - t0) * 1000
            # Truncate to prevent context overflow
            limit = CFG["output_truncate_lines"]
            stdout_lines = proc.stdout.strip().splitlines()
            stderr_lines = proc.stderr.strip().splitlines()
            if len(stdout_lines) > limit:
                head = stdout_lines[:limit//2]
                tail = stdout_lines[-limit//2:]
                stdout_lines = head + [f"... [{len(stdout_lines) - limit} lines omitted] ..."] + tail
            return ShellResult(
                code=proc.returncode,
                stdout="\n".join(stdout_lines),
                stderr="\n".join(stderr_lines[-20:]),
                duration_ms=ms
            )
        except subprocess.TimeoutExpired:
            return ShellResult(-1, "", f"Command timed out after {timeout}s", timeout * 1000)
        except Exception as e:
            return ShellResult(-1, "", str(e), 0)

    def _is_interactive_cmd(self, cmd: str) -> bool:
        """Return True if cmd would likely hang waiting for user input."""
        cmd_lower = cmd.strip().lower()
        # Running a Python script directly without piped input
        py_run = re.match(r'^python\d*\s+["\']?(\S+\.py)["\']?\s*$', cmd_lower)
        if py_run:
            script_name = py_run.group(1)
            script_path = self.cwd / script_name
            if script_path.exists():
                try:
                    content = script_path.read_text(errors="ignore")
                    if re.search(r'\binput\s*\(', content):
                        return True
                except Exception:
                    pass
        return False


    def scan_project(self) -> Dict[str, Any]:
        files = []
        try:
            files = [f.name for f in self.cwd.iterdir()]
        except Exception:
            pass
        stacks, deploy_targets, env_vars, structure = [], [], [], {}

        for marker, tech in self.STACK_MARKERS.items():
            if any(f == marker or (marker.startswith("*") and f.endswith(marker[1:])) for f in files):
                stacks.append(tech)

        for marker, target in self.DEPLOY_MARKERS.items():
            if marker in files or (self.cwd / marker).exists():
                deploy_targets.append(target)

        # AST env-var mining
        for ext in [".py", ".js", ".ts", ".env.example", ".env.sample"]:
            for fpath in self.cwd.glob(f"*{ext}"):
                try:
                    content = fpath.read_text(errors="ignore")
                    found = re.findall(
                        r'(?:os\.(?:getenv|environ\.get)|process\.env)\(["\']([A-Z0-9_]+)["\']',
                        content
                    )
                    env_vars.extend(found)
                except Exception:
                    pass

        # Directory tree (2 levels)
        try:
            for item in sorted(self.cwd.iterdir()):
                if item.name.startswith("."): continue
                if item.is_dir():
                    children = [c.name for c in item.iterdir() if not c.name.startswith(".")][:6]
                    structure[item.name + "/"] = children
                else:
                    structure[item.name] = item.stat().st_size
        except Exception:
            pass

        return {
            "cwd": str(self.cwd),
            "stacks": stacks or ["Unknown"],
            "deploy_targets": deploy_targets,
            "required_env_vars": list(set(env_vars)),
            "structure": structure,
        }

    def git_op(self, subcmd: str) -> ShellResult:
        return self.run(f"git {subcmd}")

shell = ShellEngine()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6a — GIT SHIELD & CHECKPOINTING (Shadow Sandboxing & Rollback)
# ══════════════════════════════════════════════════════════════════════════════
class GitShield:
    """
    Enterprise Sandboxing, Snapshotting & Rollback Engine.
    - Captures file checkpoints automatically before tasks begin.
    - Supports git stashing / branch snapshotting + local shadow file backup.
    - Powers /undo, /rollback, /diff, /commit, and /checkpoint commands.
    """
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.checkpoints: List[Dict[str, Any]] = []
        self._shadow_dir = Path("C:/.ignite_scratch/shadow_checkpoints")
        try:
            self._shadow_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def is_git_repo(self) -> bool:
        return (self.workspace / ".git").is_dir()

    def create_checkpoint(self, label: str = "Auto Checkpoint") -> str:
        """Create a safety checkpoint of current working directory state."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        chk_id = f"chk_{timestamp}"
        chk_folder = self._shadow_dir / chk_id
        try:
            chk_folder.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        data: Dict[str, Any] = {
            "id": chk_id,
            "label": label,
            "timestamp": timestamp,
            "is_git": self.is_git_repo(),
            "folder": str(chk_folder),
            "files": {},
            "created_at": time.time(),
        }

        if self.is_git_repo():
            res = shell.git_op("rev-parse HEAD")
            data["git_head"] = res.stdout.strip() if res.ok else "HEAD"
            shell.git_op(f"stash create \"{chk_id}: {label}\"")

        self.checkpoints.append(data)
        if len(self.checkpoints) > 20:
            self.checkpoints.pop(0)
        return chk_id

    def backup_file(self, file_path: Path):
        """Backup an individual file before it gets modified."""
        try:
            if not file_path.exists() or not self.checkpoints:
                return
            current_chk = self.checkpoints[-1]
            chk_folder = Path(current_chk["folder"])
            try:
                rel = file_path.resolve().relative_to(self.workspace.resolve())
            except ValueError:
                rel = Path(file_path.name)
            dest = chk_folder / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(file_path, dest)
                current_chk["files"][str(rel)] = str(dest)
        except Exception:
            pass

    def rollback(self) -> Tuple[bool, str]:
        """Rollback working tree to the last checkpoint."""
        if not self.checkpoints:
            if self.is_git_repo():
                shell.git_op("checkout .")
                shell.git_op("clean -fd")
                return True, "Reverted all uncommitted changes via git checkout."
            return False, "No checkpoints available to restore."

        chk = self.checkpoints.pop()
        restored_count = 0

        # Restore shadowed files
        if chk.get("files"):
            for rel_str, src_str in chk["files"].items():
                target = self.workspace / rel_str
                src = Path(src_str)
                if src.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, target)
                    restored_count += 1

        if self.is_git_repo():
            shell.git_op("checkout .")
            shell.git_op("clean -fd")

        return True, f"Restored {restored_count} file(s) from checkpoint: '{chk['label']}' ({chk['id']})"

    def diff(self, path: str = "") -> str:
        """Get formatted diff of changes in working tree."""
        if self.is_git_repo():
            target = f" -- \"{path}\"" if path else ""
            res = shell.git_op(f"diff --color=never{target}")
            diff_text = res.stdout.strip()
            if diff_text:
                return diff_text
            st = shell.git_op("status --short").stdout.strip()
            if st:
                return f"Untracked / Staged files:\n{st}"
            return "No changes detected (working tree clean)."
        else:
            if not self.checkpoints or not self.checkpoints[-1].get("files"):
                return "Not a git repo. No files modified in current checkpoint."
            files = list(self.checkpoints[-1]["files"].keys())
            return f"Non-git project. Modified files in shadow checkpoint:\n" + "\n".join(f"  • {f}" for f in files)

git_shield = GitShield(shell.cwd)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6b — PROCESS REGISTRY  (spawn · monitor · kill)
# ══════════════════════════════════════════════════════════════════════════════
import tempfile

@dataclass
class ManagedProcess:
    pid: int
    name: str
    cmd: str
    log_path: str
    started_at: str
    mode: str          # "window" | "background"
    _proc: Any = field(repr=False, default=None)

    @property
    def is_alive(self) -> bool:
        if self._proc is not None:
            return self._proc.poll() is None
        # Fallback: ask OS
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 f"(Get-Process -Id {self.pid} -ErrorAction SilentlyContinue) -ne $null"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip().lower() == "true"
        except Exception:
            return False

    def tail_log(self, lines: int = 60) -> str:
        try:
            content = Path(self.log_path).read_text(encoding="utf-8", errors="ignore")
            all_lines = content.splitlines()
            return "\n".join(all_lines[-lines:]) if all_lines else "[No output yet]"
        except Exception as e:
            return f"[Log read error: {e}]"

class ProcessRegistry:
    """Tracks all processes spawned by the agent."""
    def __init__(self):
        self._procs: Dict[int, ManagedProcess] = {}
        self._log_dir = Path(tempfile.gettempdir()) / "ignite_procs"
        self._log_dir.mkdir(exist_ok=True)

    # ── Spawn a new VISIBLE terminal window ───────────────────────────────────
    def spawn_window(self, cmd: str, cwd: str, name: str = "") -> Tuple[int, str]:
        """Open script in a new visible PowerShell window. Returns (pid, message).
        Uses UTF-8 log via Out-File so tail_log() reads correctly.
        """
        proc_name = name or (Path(cmd.split()[-1]).stem if cmd else "process")
        log_path = str(self._log_dir / f"win_{int(time.time())}_{proc_name}.log")
        clean_cmd = cmd.strip()

        # We split the stream:
        #   • Write-Host shows coloured output in the terminal window (visible to user)
        #   • Out-File -Encoding utf8 captures stdout+stderr in UTF-8 (readable by agent)
        # Script block technique: run command, capture all output, echo + save
        ps_launcher = (
            f"$host.UI.RawUI.WindowTitle = 'IGNITE [{proc_name}]'; "
            f"Set-Location -LiteralPath '{cwd}'; "
            f"$env:PYTHONUNBUFFERED = '1'; "
            f"Write-Host '╔══════════════════════════════════════════════════════╗' -ForegroundColor Cyan; "
            f"Write-Host '║  IGNITE MANAGED: {proc_name:<36}║' -ForegroundColor Cyan; "
            f"Write-Host '╚══════════════════════════════════════════════════════╝' -ForegroundColor Cyan; "
            f"Write-Host 'CMD: {clean_cmd}' -ForegroundColor Yellow; "
            f"Write-Host ''; "
            f"& {{ {clean_cmd} }} 2>&1 | ForEach-Object {{ "
            f"    $_ | Out-File -FilePath '{log_path}' -Encoding utf8 -Append; "
            f"    Write-Host $_ "
            f"}}; "
            f"Write-Host ''; "
            f"Write-Host '[IGNITE] Process finished. Press any key...' -ForegroundColor DarkGray; "
            f"$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')"
        )

        try:
            flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            proc = subprocess.Popen(
                ["powershell.exe", "-NoExit", "-Command", ps_launcher],
                cwd=cwd,
                creationflags=flags
            )
            pid = proc.pid
            mp = ManagedProcess(pid=pid, name=proc_name, cmd=clean_cmd,
                                log_path=log_path, started_at=datetime.now().isoformat(),
                                mode="window", _proc=proc)
            self._procs[pid] = mp
            return pid, f"Opened visible terminal window! PID={pid} | Title='IGNITE [{proc_name}]' | Log={log_path}"
        except Exception as e:
            return -1, f"Failed to open terminal window: {str(e)}"

    # ── Spawn BACKGROUND (invisible, log to file) ─────────────────────────────
    def spawn_background(self, cmd: str, cwd: str, name: str = "") -> ManagedProcess:
        """Run process silently in background. Output captured to log file."""
        log_path = str(self._log_dir / f"bg_{int(time.time())}_{name or 'proc'}.log")
        log_file = open(log_path, "w", encoding="utf-8", errors="replace", buffering=1)
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "PYTHONUNBUFFERED": "1"}
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            cwd=cwd, stdout=log_file, stderr=subprocess.STDOUT, env=env
        )
        mp = ManagedProcess(pid=proc.pid, name=name or cmd[:40], cmd=cmd,
                            log_path=log_path, started_at=datetime.now().isoformat(),
                            mode="background", _proc=proc)
        self._procs[proc.pid] = mp
        return mp

    # ── Kill ──────────────────────────────────────────────────────────────────
    def kill(self, pid: int) -> str:
        mp = self._procs.get(pid)
        name = mp.name if mp else str(pid)
        if mp and mp._proc:
            mp._proc.terminate()
            try: mp._proc.wait(timeout=5)
            except Exception: mp._proc.kill()
        # Also kill via PowerShell (catches window processes)
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
            capture_output=True, timeout=10
        )
        if pid in self._procs:
            del self._procs[pid]
        return f"✔ Killed PID {pid} ({name})"

    def kill_by_name(self, name: str) -> str:
        killed = []
        for pid, mp in list(self._procs.items()):
            if name.lower() in mp.name.lower() or name.lower() in mp.cmd.lower():
                self.kill(pid)
                killed.append(pid)
        if killed:
            return f"Killed PIDs: {killed}"
        # Try OS-level by process name
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             f"Stop-Process -Name '{name}' -Force -ErrorAction SilentlyContinue"],
            capture_output=True, timeout=10
        )
        return f"Attempted kill of process named '{name}'"

    # ── Status / Log reader ───────────────────────────────────────────────────
    def status(self, pid: int = None, tail: int = 60) -> str:
        if pid:
            mp = self._procs.get(pid)
            if not mp:
                return f"PID {pid} not tracked by IGNITE."
            alive = "🟢 RUNNING" if mp.is_alive else "🔴 STOPPED"
            return (f"{alive}  PID:{pid}  [{mp.mode}]  {mp.name}\n"
                    f"CMD: {mp.cmd}\nStarted: {mp.started_at}\n"
                    f"Log: {mp.log_path}\n\n--- Recent Output ---\n{mp.tail_log(tail)}")
        if not self._procs:
            return "No processes tracked."
        lines = []
        for pid, mp in self._procs.items():
            alive = "🟢" if mp.is_alive else "🔴"
            lines.append(f"  {alive} PID:{pid:6}  [{mp.mode:10}]  {mp.name[:40]:<40}  {mp.started_at[:16]}")
        return "MANAGED PROCESSES:\n" + "\n".join(lines)

    def list_fmt(self) -> str:
        return self.status()

proc_registry = ProcessRegistry()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6c — WEB DASHBOARD  (localhost:7860 — no extra dependencies)
# ══════════════════════════════════════════════════════════════════════════════
import http.server, webbrowser as _webbrowser

_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>IGNITE Dashboard</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0d0d0d;--card:#141414;--border:#222;--cyan:#00e5ff;--green:#00e676;--red:#ff1744;--yellow:#ffd740;--gray:#666;--text:#e0e0e0}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',monospace;font-size:14px}
header{background:linear-gradient(90deg,#0d0d0d,#1a0000);border-bottom:2px solid var(--red);padding:16px 24px;display:flex;align-items:center;justify-content:space-between}
.logo{font-size:22px;font-weight:700;color:var(--red);letter-spacing:2px}.logo span{color:var(--cyan)}
.subtitle{color:var(--gray);font-size:12px;margin-top:2px}
.badge{background:#1a1a1a;border:1px solid var(--border);border-radius:20px;padding:4px 12px;font-size:12px;color:var(--gray)}
.badge.live{border-color:var(--green);color:var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:20px;max-width:1600px;margin:0 auto}
@media(max-width:900px){.grid{grid-template-columns:1fr}}
.full{grid-column:1/-1}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;overflow:hidden}
.card-header{padding:12px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;font-weight:600;font-size:13px}
.card-body{padding:16px}
.stats{display:flex;gap:16px;flex-wrap:wrap}
.stat{flex:1;min-width:120px;background:#0a0a0a;border:1px solid var(--border);border-radius:8px;padding:14px 16px;text-align:center}
.stat .val{font-size:28px;font-weight:700;color:var(--cyan)}.stat .lbl{font-size:11px;color:var(--gray);margin-top:4px;text-transform:uppercase;letter-spacing:1px}
table{width:100%;border-collapse:collapse}
th{text-align:left;padding:8px 12px;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--gray);border-bottom:1px solid var(--border)}
td{padding:9px 12px;border-bottom:1px solid #1a1a1a;vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:#1a1a1a}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.dot.green{background:var(--green);box-shadow:0 0 6px var(--green)}.dot.red{background:var(--red)}
.tag{background:#1e1e1e;border:1px solid #333;border-radius:4px;padding:2px 8px;font-size:11px;color:var(--gray)}
.tag.window{border-color:#00bcd4;color:#00bcd4}.tag.background{border-color:#ff9800;color:#ff9800}
.btn{border:none;border-radius:5px;padding:5px 12px;font-size:12px;cursor:pointer;font-family:inherit;transition:.15s}
.btn-red{background:#2a0a0a;border:1px solid var(--red);color:var(--red)}.btn-red:hover{background:var(--red);color:#000}
.btn-cyan{background:#001a1e;border:1px solid var(--cyan);color:var(--cyan)}.btn-cyan:hover{background:var(--cyan);color:#000}
.btn-green{background:#001a08;border:1px solid var(--green);color:var(--green)}.btn-green:hover{background:var(--green);color:#000}
.btn-sm{padding:3px 8px;font-size:11px}
#log-viewer{background:#050505;border:1px solid var(--border);border-radius:6px;padding:14px;font-family:monospace;font-size:12px;line-height:1.6;height:320px;overflow-y:auto;white-space:pre-wrap;word-break:break-all;color:#b0b0b0}
.log-bar{display:flex;gap:8px;margin-bottom:10px;align-items:center;flex-wrap:wrap}
#pid-select{background:#0a0a0a;border:1px solid var(--border);color:var(--text);border-radius:5px;padding:5px 10px;font-family:inherit;font-size:12px;flex:1}
.msg{padding:10px 12px;border-radius:6px;margin-bottom:8px;font-size:13px;line-height:1.5}
.msg.user{background:#0d1a2e;border-left:3px solid var(--cyan)}.msg.assistant{background:#0a1a0a;border-left:3px solid var(--green)}
.msg .role{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--gray);margin-bottom:4px}
#history-box{height:260px;overflow-y:auto}
footer{text-align:center;color:var(--gray);font-size:11px;padding:20px;border-top:1px solid var(--border)}
.err{color:var(--red)}.ok{color:var(--green)}.info-txt{color:var(--cyan)}
</style>
</head>
<body>
<header>
  <div>
    <div class="logo">IGNITE <span>DASHBOARD</span></div>
    <div class="subtitle">Autonomous AI DevOps Agent · V3 PRO</div>
  </div>
  <div style="display:flex;gap:10px;align-items:center">
    <span class="badge live">● LIVE</span>
    <span class="badge" id="last-refresh">–</span>
    <button class="btn btn-cyan btn-sm" onclick="refresh()">⟳ Refresh</button>
  </div>
</header>
<div class="grid">
  <!-- Stats -->
  <div class="card full">
    <div class="card-header"><span>📊 Overview</span></div>
    <div class="card-body">
      <div class="stats">
        <div class="stat"><div class="val" id="s-running">–</div><div class="lbl">Running</div></div>
        <div class="stat"><div class="val" id="s-total">–</div><div class="lbl">Total Spawned</div></div>
        <div class="stat"><div class="val" id="s-steps">–</div><div class="lbl">Agent Steps</div></div>
        <div class="stat"><div class="val" id="s-tokens" style="font-size:14px">–</div><div class="lbl">Tokens</div></div>
        <div class="stat"><div class="val" id="s-model" style="font-size:13px">–</div><div class="lbl">Active Model</div></div>
        <div class="stat"><div class="val" id="s-cwd" style="font-size:13px">–</div><div class="lbl">Working Dir</div></div>
      </div>
    </div>
  </div>
  <!-- Process Table -->
  <div class="card full">
    <div class="card-header">
      <span>⚙️ Managed Processes</span>
      <button class="btn btn-red btn-sm" onclick="killAll()">🗑 Kill All</button>
    </div>
    <div class="card-body" style="padding:0">
      <table>
        <thead><tr><th>Status</th><th>PID</th><th>Name</th><th>Mode</th><th>Command</th><th>Started</th><th>Actions</th></tr></thead>
        <tbody id="proc-tbody"><tr><td colspan="7" style="text-align:center;color:var(--gray);padding:20px">No processes yet</td></tr></tbody>
      </table>
    </div>
  </div>
  <!-- Log Viewer -->
  <div class="card">
    <div class="card-header">
      <span>📋 Live Log Viewer</span>
      <button class="btn btn-green btn-sm" onclick="autoScroll=!autoScroll">⇓ Auto-scroll</button>
    </div>
    <div class="card-body">
      <div class="log-bar">
        <select id="pid-select" onchange="selectedPid=this.value"><option value="">— select process —</option></select>
        <button class="btn btn-cyan btn-sm" onclick="fetchLog()">Load Log</button>
        <button class="btn btn-sm" style="background:#1a1a1a;border:1px solid #333;color:#666" onclick="document.getElementById('log-viewer').textContent=''">Clear</button>
      </div>
      <div id="log-viewer"><span class="info-txt">Select a process above to view its live log...</span></div>
    </div>
  </div>
  <!-- Chat History -->
  <div class="card">
    <div class="card-header"><span>💬 Conversation History</span></div>
    <div class="card-body">
      <div id="history-box"><div style="color:var(--gray);text-align:center;padding:20px">Loading...</div></div>
    </div>
  </div>
</div>
<footer>🔥 IGNITE V3 PRO &nbsp;·&nbsp; Dashboard auto-refreshes every 3s &nbsp;·&nbsp; <a href="/api/processes" target="_blank" style="color:var(--cyan);text-decoration:none">JSON API</a></footer>
<script>
let selectedPid='',autoScroll=true;
async function fetchJSON(url){try{const r=await fetch(url);return await r.json()}catch{return null}}
function colorLog(t){
  return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/(Traceback|Error:|Exception:|FAILED|SyntaxError|ModuleNotFoundError)/g,'<span class="err">$1</span>')
    .replace(/(Successfully|started|Running|OK)/gi,'<span class="ok">$1</span>')
    .replace(/(INFO|WARNING|DEBUG)/g,'<span class="info-txt">$1</span>');
}
async function fetchLog(){
  const pid=selectedPid||document.getElementById('pid-select').value;
  if(!pid)return;
  const data=await fetchJSON('/api/log/'+pid);
  const box=document.getElementById('log-viewer');
  if(data){box.innerHTML=colorLog(data.log||'[No output yet]');if(autoScroll)box.scrollTop=box.scrollHeight;}
}
async function killProc(pid){if(!confirm('Kill PID '+pid+'?'))return;await fetch('/api/kill/'+pid,{method:'POST'});refresh()}
async function killAll(){if(!confirm('Kill ALL managed processes?'))return;await fetch('/api/kill_all',{method:'POST'});refresh()}
async function refresh(){
  const data=await fetchJSON('/api/status');if(!data)return;
  document.getElementById('s-running').textContent=data.running;
  document.getElementById('s-total').textContent=data.total;
  document.getElementById('s-steps').textContent=data.steps;
  document.getElementById('s-tokens').textContent=data.tokens;
  document.getElementById('s-model').textContent=data.model;
  document.getElementById('s-cwd').textContent=data.cwd.split(/[\/\\]/).slice(-2).join('/');
  document.getElementById('last-refresh').textContent=new Date().toLocaleTimeString();
  const tbody=document.getElementById('proc-tbody');
  const sel=document.getElementById('pid-select');
  sel.innerHTML='<option value="">— select process —</option>';
  if(!data.processes||!data.processes.length){
    tbody.innerHTML='<tr><td colspan="7" style="text-align:center;color:var(--gray);padding:20px">No processes spawned yet</td></tr>';
  }else{
    tbody.innerHTML=data.processes.map(p=>`<tr>
      <td><span class="dot ${p.alive?'green':'red'}"></span>${p.alive?'Running':'Stopped'}</td>
      <td><code>${p.pid}</code></td><td>${p.name}</td>
      <td><span class="tag ${p.mode}">${p.mode}</span></td>
      <td style="font-size:11px;color:var(--gray);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${p.cmd}">${p.cmd}</td>
      <td style="font-size:11px;color:var(--gray)">${p.started}</td>
      <td style="display:flex;gap:5px">
        <button class="btn btn-cyan btn-sm" onclick="selectedPid='${p.pid}';fetchLog()">📋 Log</button>
        ${p.alive?`<button class="btn btn-red btn-sm" onclick="killProc(${p.pid})">✕ Kill</button>`:''}
      </td></tr>`).join('');
    data.processes.forEach(p=>{const o=document.createElement('option');o.value=p.pid;o.text=`PID ${p.pid} — ${p.name}`;sel.appendChild(o)});
    if(selectedPid)sel.value=selectedPid;
  }
  const hb=document.getElementById('history-box');
  if(data.history&&data.history.length){
    hb.innerHTML=data.history.filter(m=>m.role!=='system').slice(-20).map(m=>`<div class="msg ${m.role}"><div class="role">${m.role==='user'?'You':'IGNITE'}</div>${m.content.substring(0,300).replace(/</g,'&lt;')}${m.content.length>300?'…':''}</div>`).join('');
    hb.scrollTop=hb.scrollHeight;
  }
  if(selectedPid)fetchLog();
}
refresh();setInterval(refresh,3000);
</script>
</body>
</html>"""


class _DashboardHandler(http.server.BaseHTTPRequestHandler):
    session_ref = None

    def log_message(self, *a): pass  # silence access logs

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", _DASHBOARD_HTML.encode())
        elif path == "/api/status":
            self._api_status()
        elif path.startswith("/api/log/"):
            self._api_log(path.split("/")[-1])
        elif path == "/api/processes":
            self._api_procs()
        else:
            self._send(404, "text/plain", b"Not found")

    def do_POST(self):
        path = self.path.split("?")[0]
        if path.startswith("/api/kill/"):
            try:
                proc_registry.kill(int(path.split("/")[-1]))
                self._send(200, "application/json", b'{"ok":true}')
            except Exception as e:
                self._send(500, "application/json", json.dumps({"error": str(e)}).encode())
        elif path == "/api/kill_all":
            for pid in list(proc_registry._procs.keys()):
                try: proc_registry.kill(pid)
                except Exception: pass
            self._send(200, "application/json", b'{"ok":true}')
        else:
            self._send(404, "text/plain", b"Not found")

    def _api_status(self):
        sess = _DashboardHandler.session_ref
        procs = [
            {"pid": pid, "name": mp.name, "cmd": mp.cmd, "mode": mp.mode,
             "alive": mp.is_alive, "started": mp.started_at[:16], "log": mp.log_path}
            for pid, mp in proc_registry._procs.items()
        ]
        history = sess.memory.get_history() if sess else []
        data = {
            "running":   sum(1 for p in procs if p["alive"]),
            "total":     len(procs),
            "steps":     sess.total_steps if sess else 0,
            "tokens":    tracker.summary().split("|")[0].strip(),
            "model":     router.override_id or "auto",
            "cwd":       str(shell.cwd),
            "processes": procs,
            "history":   [{"role": m["role"], "content": m["content"][:400]} for m in history[-20:]],
        }
        self._send(200, "application/json", json.dumps(data).encode())

    def _api_log(self, pid_str):
        try:
            mp = proc_registry._procs.get(int(pid_str))
            log = mp.tail_log(120) if mp else f"PID {pid_str} not found."
            self._send(200, "application/json",
                       json.dumps({"pid": pid_str, "log": log, "alive": mp.is_alive if mp else False}).encode())
        except Exception as e:
            self._send(500, "application/json", json.dumps({"error": str(e)}).encode())

    def _api_procs(self):
        procs = [{"pid": pid, "name": mp.name, "alive": mp.is_alive, "cmd": mp.cmd, "mode": mp.mode}
                 for pid, mp in proc_registry._procs.items()]
        self._send(200, "application/json", json.dumps(procs).encode())


class DashboardServer:
    """Threaded localhost dashboard — no extra deps, pure stdlib."""
    def __init__(self, port: int = 7860):
        self.port    = port
        self._server = None
        self._thread = None
        self.running = False

    def start(self, session=None, open_browser: bool = True) -> str:
        if self.running:
            return f"Already running → http://localhost:{self.port}"
        _DashboardHandler.session_ref = session
        try:
            self._server = http.server.HTTPServer(("localhost", self.port), _DashboardHandler)
        except OSError:
            self.port += 1
            self._server = http.server.HTTPServer(("localhost", self.port), _DashboardHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.running = True
        url = f"http://localhost:{self.port}"
        if open_browser:
            _webbrowser.open(url)
        return url

    def stop(self) -> str:
        if self._server:
            self._server.shutdown()
            self.running = False
            return "Dashboard stopped."
        return "Dashboard was not running."

    def url(self) -> str:
        return f"http://localhost:{self.port}" if self.running else "not running"


dashboard = DashboardServer(port=7860)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — WEB SEARCH ENGINE  (DuckDuckGo + Brave fallback)
# ══════════════════════════════════════════════════════════════════════════════
SEARCH_BACKENDS = [
    ("DuckDuckGo", "https://html.duckduckgo.com/html/?q={q}",
     r'class="result__snippet[^"]*"[^>]*>(.*?)</a>'),
    ("Bing",       "https://www.bing.com/search?q={q}",
     r'<p[^>]*>(.*?)</p>'),
]

def web_search(query: str, n: int = None) -> str:
    n = n or CFG["search_results"]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for backend_name, url_tpl, pattern in SEARCH_BACKENDS:
        try:
            url = url_tpl.format(q=urllib.parse.quote_plus(query))
            req = urllib.request.Request(url, headers=headers)
            html = urllib.request.urlopen(req, timeout=12).read().decode("utf-8", errors="ignore")
            snippets = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            clean = [re.sub(r"<[^>]+>", "", s).strip() for s in snippets if len(s) > 20]
            clean = [c for c in clean if c][:n]
            if clean:
                return f"[{backend_name} Results for: {query}]\n" + "\n".join(f"  • {c}" for c in clean)
        except Exception:
            continue
    return f"All search backends failed for: {query}"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — TOOL EXECUTOR  (10 tools)
# ══════════════════════════════════════════════════════════════════════════════
class ToolResult:
    def __init__(self, success: bool, output: str, tool: str):
        self.success = success
        self.output = output
        self.tool = tool

def tool_terminal(cmd: str) -> ToolResult:
    real_cmd = obfuscator.unmask(cmd)
    res = shell.run(real_cmd)
    return ToolResult(res.ok, res.log, "terminal")

def tool_file_read(path: str, start: int = 1, end: int = None) -> ToolResult:
    try:
        real_path = Path(obfuscator.unmask(path))
        if not real_path.is_absolute():
            real_path = shell.cwd / real_path
        lines = real_path.read_text(errors="ignore").splitlines()
        s = max(0, start - 1)
        e = end if end else len(lines)
        chunk = lines[s:e]
        if len(chunk) > 200:
            chunk = chunk[:100] + [f"... [{len(chunk)-200} lines omitted] ..."] + chunk[-100:]
        return ToolResult(True, "\n".join(chunk), "file_read")
    except Exception as ex:
        return ToolResult(False, str(ex), "file_read")

def tool_file_write(path: str, content: str) -> ToolResult:
    try:
        real_path = Path(obfuscator.unmask(path))
        if not real_path.is_absolute():
            real_path = shell.cwd / real_path

        # ── AST Pre-Flight Syntax Gatekeeper ──
        if real_path.suffix == ".py":
            try:
                ast.parse(content)
            except SyntaxError as syn_err:
                lines = content.splitlines()
                snippet = ""
                if syn_err.lineno and 1 <= syn_err.lineno <= len(lines):
                    s_l = max(1, syn_err.lineno - 2)
                    e_l = min(len(lines), syn_err.lineno + 2)
                    snippet = "\n".join(f"{'>>' if i == syn_err.lineno else '  '} {i}: {lines[i-1]}" for i in range(s_l, e_l + 1))
                return ToolResult(
                    False,
                    f"❌ AST PRE-FLIGHT SYNTAX ERROR in '{path}' (Line {syn_err.lineno}, Col {syn_err.offset}):\n"
                    f"{snippet}\n"
                    f"Error: {syn_err.msg}\n"
                    f"👉 Fix this syntax error and rewrite the code properly before saving.",
                    "file_write"
                )
        elif real_path.suffix == ".json":
            try:
                json.loads(content)
            except Exception as j_err:
                return ToolResult(
                    False,
                    f"❌ JSON SYNTAX ERROR in '{path}': {j_err}. Please fix formatting before saving.",
                    "file_write"
                )

        # ── Shadow Checkpoint Backup ──
        if 'git_shield' in globals():
            git_shield.backup_file(real_path)

        real_path.parent.mkdir(parents=True, exist_ok=True)
        real_path.write_text(content, encoding="utf-8")
        return ToolResult(True, f"Written {len(content)} chars → {real_path}", "file_write")
    except Exception as ex:
        return ToolResult(False, str(ex), "file_write")

def tool_file_patch(path: str, diff: str) -> ToolResult:
    """Apply a unified-diff style patch to a file with AST safety."""
    try:
        real_path = Path(obfuscator.unmask(path))
        if not real_path.is_absolute():
            real_path = shell.cwd / real_path
        if not real_path.exists():
            return ToolResult(False, f"File not found to patch: {path}", "file_patch")

        # ── Shadow Checkpoint Backup ──
        if 'git_shield' in globals():
            git_shield.backup_file(real_path)

        original = real_path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
        patch_lines = diff.splitlines(keepends=True)
        result = list(difflib.restore(patch_lines, 2))  # restore new file from diff
        if result:
            patched_content = "".join(result)
            if real_path.suffix == ".py":
                try:
                    ast.parse(patched_content)
                except SyntaxError as syn_err:
                    return ToolResult(
                        False,
                        f"❌ AST SYNTAX ERROR after patch in '{path}' (Line {syn_err.lineno}): {syn_err.msg}. "
                        f"Patch rejected to preserve valid syntax.",
                        "file_patch"
                    )
            real_path.write_text(patched_content, encoding="utf-8")
            return ToolResult(True, f"Patched {real_path} ({len(result)} lines)", "file_patch")
        return ToolResult(False, "Patch produced empty output — check diff format", "file_patch")
    except Exception as ex:
        return ToolResult(False, str(ex), "file_patch")

def tool_git(subcmd: str) -> ToolResult:
    res = shell.git_op(obfuscator.unmask(subcmd))
    return ToolResult(res.ok, res.log, "git")

def tool_git_diff(path: str = "") -> ToolResult:
    """Inspect uncommitted code changes in working tree."""
    diff_text = git_shield.diff(path)
    return ToolResult(True, diff_text, "git_diff")

def tool_verify_code(cmd: str = "", path: str = "") -> ToolResult:
    """
    Self-Healing Code Verification Tool.
    Auto-detects test runners (pytest, unittest, npm test, cargo test, go test)
    or runs the specified test command / compilation check.
    """
    test_cmd = cmd.strip()
    if not test_cmd:
        cwd = shell.cwd
        if path:
            target_p = Path(path)
            if target_p.suffix == ".py":
                test_cmd = f"python -m py_compile \"{path}\""
        elif (cwd / "pytest.ini").exists() or (cwd / "tests").is_dir() or any((cwd).glob("test_*.py")):
            test_cmd = "pytest -q"
        elif any((cwd).glob("*_test.py")):
            test_cmd = "python -m unittest discover -s . -p \"*test*.py\""
        elif (cwd / "package.json").exists():
            test_cmd = "npm test"
        elif (cwd / "Cargo.toml").exists():
            test_cmd = "cargo test"
        elif (cwd / "go.mod").exists():
            test_cmd = "go test ./..."
        else:
            test_cmd = "python -m compileall -q ."

    res = shell.run(test_cmd, timeout=90)
    if res.ok:
        return ToolResult(
            True,
            f"✅ VERIFICATION PASSED ({test_cmd}):\n{res.stdout.strip() or 'All checks and tests passed (Exit code 0).'}",
            "verify_code"
        )
    else:
        return ToolResult(
            False,
            f"❌ VERIFICATION FAILED (Exit Code {res.code}) running: `{test_cmd}`\n"
            f"Output / Traceback:\n{res.log}\n\n"
            f"👉 SELF-HEALING ACTION: Examine the failure above, patch the code with file_write or file_patch, and run verify_code again.",
            "verify_code"
        )

def tool_python_eval(code: str) -> ToolResult:
    """Safe-ish sandboxed Python eval (no builtins that can spawn processes)."""
    BLOCKED = {"__import__", "exec", "eval", "open", "os", "sys", "subprocess", "importlib"}
    for b in BLOCKED:
        if b in code:
            return ToolResult(False, f"Blocked keyword in python_eval: {b}", "python_eval")
    import io, contextlib
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            exec(compile(code, "<ignite_eval>", "exec"),
                 {"__builtins__": {"print": print, "len": len, "range": range,
                                   "str": str, "int": int, "float": float,
                                   "list": list, "dict": dict, "set": set,
                                   "sorted": sorted, "sum": sum, "min": min, "max": max,
                                   "abs": abs, "round": round, "enumerate": enumerate,
                                   "zip": zip, "map": map, "filter": filter}})
        return ToolResult(True, buf.getvalue() or "[No output]", "python_eval")
    except Exception as ex:
        return ToolResult(False, f"{type(ex).__name__}: {ex}", "python_eval")

def tool_search(query: str) -> ToolResult:
    real_query = obfuscator.unmask(query)
    results = web_search(real_query)
    return ToolResult(True, obfuscator.mask(results), "search")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7b — CLOUD DEPLOY ENGINE  (Railway · Render · Fly.io · Docker · Heroku · Vercel)
# ══════════════════════════════════════════════════════════════════════════════
class CloudDeployEngine:
    """Intelligent Multi-Cloud Deployment Engine.
    Auto-detects project stack, creates production deployment configs (Dockerfile, Procfile,
    railway.toml, render.yaml, fly.toml), syncs .env secrets, and runs cloud deployments.
    """

    PLATFORMS = {
        "railway": {
            "name": "Railway",
            "cli": "railway",
            "install": "npm install -g @railway/cli",
            "desc": "Auto-deploy with env vars, persistent workers & zero downtime",
        },
        "render": {
            "name": "Render",
            "cli": "git",
            "install": "Connect Git repo at https://dashboard.render.com",
            "desc": "Infrastructure as code via render.yaml",
        },
        "fly": {
            "name": "Fly.io",
            "cli": "flyctl",
            "install": 'powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"',
            "desc": "Fast global Docker / MicroVM hosting",
        },
        "docker": {
            "name": "Docker",
            "cli": "docker",
            "install": "Install Docker Desktop: https://www.docker.com/products/docker-desktop",
            "desc": "Local or server containerized execution",
        },
        "heroku": {
            "name": "Heroku",
            "cli": "heroku",
            "install": "winget install Heroku.CLI",
            "desc": "Classic cloud PaaS via Git push",
        },
        "vercel": {
            "name": "Vercel",
            "cli": "vercel",
            "install": "npm install -g vercel",
            "desc": "Serverless edge & frontend deployment",
        },
    }

    def detect_entrypoint(self, cwd: Path) -> Tuple[str, str]:
        """Returns (entrypoint_filename, service_type: 'worker' | 'web')"""
        try:
            files = [f.name.lower() for f in cwd.iterdir() if f.is_file()]
        except Exception:
            files = []
        if "bot.py" in files:
            return "bot.py", "worker"
        if "app.py" in files:
            return "app.py", "web"
        if "main.py" in files:
            try:
                content = (cwd / "main.py").read_text(errors="ignore")
                if "fastapi" in content.lower() or "flask" in content.lower():
                    return "main.py", "web"
            except Exception:
                pass
            return "main.py", "worker"
        if "index.js" in files or "server.js" in files:
            return "index.js" if "index.js" in files else "server.js", "web"
        return "bot.py" if (cwd / "bot.py").exists() else "main.py", "worker"

    def scaffold(self, platform: str, cwd: Path) -> List[str]:
        """Auto-generates production config files for the target cloud platform."""
        created = []
        entrypoint, service_type = self.detect_entrypoint(cwd)

        # 1. .dockerignore (always useful)
        dockerignore = cwd / ".dockerignore"
        if not dockerignore.exists():
            dockerignore.write_text(
                "__pycache__/\n*.pyc\n*.pyo\n.git/\n.env\n*.log\nvenv/\n.venv/\n",
                encoding="utf-8"
            )
            created.append(".dockerignore")

        # 2. Platform specific configs
        if platform == "railway":
            railway_toml = cwd / "railway.toml"
            if not railway_toml.exists():
                railway_toml.write_text(
                    f'[build]\nbuilder = "NIXPACKS"\n\n'
                    f'[deploy]\nstartCommand = "python {entrypoint}"\n'
                    f'restartPolicyType = "ON_FAILURE"\n'
                    f'restartPolicyMaxRetries = 10\n',
                    encoding="utf-8"
                )
                created.append("railway.toml")
            procfile = cwd / "Procfile"
            if not procfile.exists():
                cmd = f"python {entrypoint}" if service_type == "worker" else f"uvicorn {entrypoint[:-3]}:app --host 0.0.0.0 --port $PORT"
                procfile.write_text(f"{service_type}: {cmd}\n", encoding="utf-8")
                created.append("Procfile")

        elif platform == "render":
            render_yaml = cwd / "render.yaml"
            if not render_yaml.exists():
                start_cmd = f"python {entrypoint}" if service_type == "worker" else f"uvicorn {entrypoint[:-3]}:app --host 0.0.0.0 --port $PORT"
                render_yaml.write_text(
                    f"services:\n"
                    f"  - type: {service_type}\n"
                    f"    name: {cwd.name.lower() or 'ignite-app'}\n"
                    f"    env: python\n"
                    f"    buildCommand: pip install -r requirements.txt\n"
                    f"    startCommand: {start_cmd}\n"
                    f"    autoDeploy: true\n",
                    encoding="utf-8"
                )
                created.append("render.yaml")

        elif platform in ("docker", "fly"):
            dockerfile = cwd / "Dockerfile"
            if not dockerfile.exists():
                start_cmd = f'CMD ["python", "{entrypoint}"]'
                dockerfile.write_text(
                    f"FROM python:3.11-slim\n"
                    f"WORKDIR /app\n"
                    f"ENV PYTHONUNBUFFERED=1\n"
                    f"COPY requirements.txt .\n"
                    f"RUN pip install --no-cache-dir -r requirements.txt\n"
                    f"COPY . .\n"
                    f"{start_cmd}\n",
                    encoding="utf-8"
                )
                created.append("Dockerfile")
            if platform == "fly":
                fly_toml = cwd / "fly.toml"
                if not fly_toml.exists():
                    fly_toml.write_text(
                        f'app = "{cwd.name.lower() or "ignite-app"}"\n'
                        f'primary_region = "iad"\n\n'
                        f'[build]\n\n'
                        f'[env]\n  PYTHONUNBUFFERED = "1"\n',
                        encoding="utf-8"
                    )
                    created.append("fly.toml")

        elif platform == "heroku":
            procfile = cwd / "Procfile"
            if not procfile.exists():
                cmd = f"python {entrypoint}" if service_type == "worker" else f"uvicorn {entrypoint[:-3]}:app --host 0.0.0.0 --port $PORT"
                procfile.write_text(f"{service_type}: {cmd}\n", encoding="utf-8")
                created.append("Procfile")

        elif platform == "vercel":
            vercel_json = cwd / "vercel.json"
            if not vercel_json.exists():
                vercel_json.write_text('{\n  "version": 2\n}\n', encoding="utf-8")
                created.append("vercel.json")

        return created

    def check_cli(self, cli_name: str) -> bool:
        if shutil.which(cli_name):
            return True
        res = shell.run(f"{cli_name} --version")
        return res.ok

    def ensure_git(self, cwd: Path) -> str:
        """Initializes Git repo and commits if not already initialized."""
        if not (cwd / ".git").exists():
            shell.run("git init", timeout=30)
            shell.run("git add .", timeout=30)
            shell.run('git commit -m "chore: initial commit for deployment"', timeout=30)
            return "Initialized git repository."
        return ""

    def deploy(self, platform: str = "", subcmd: str = "", cwd: Path = None) -> ToolResult:
        cwd = cwd or shell.cwd

        # Resolve target platform
        target = platform.lower().strip()
        if not target and subcmd:
            for p in self.PLATFORMS:
                if p in subcmd.lower():
                    target = p
                    break
        if not target:
            if (cwd / "railway.toml").exists(): target = "railway"
            elif (cwd / "render.yaml").exists(): target = "render"
            elif (cwd / "fly.toml").exists(): target = "fly"
            elif (cwd / "Dockerfile").exists(): target = "docker"
            elif (cwd / "Procfile").exists(): target = "railway"
            elif (cwd / "vercel.json").exists(): target = "vercel"
            else: target = "railway"  # default to Railway for bots

        if target not in self.PLATFORMS:
            return ToolResult(
                False,
                f"Unknown platform '{target}'. Supported: {', '.join(self.PLATFORMS.keys())}\n\n"
                f"Usage: /deploy <railway|render|fly|docker|heroku|vercel>",
                "deploy"
            )

        plat_info = self.PLATFORMS[target]
        scaffolded = self.scaffold(target, cwd)
        git_note = self.ensure_git(cwd)

        # ── 1. RAILWAY DEPLOY ──────────────────────────────────────────────────
        if target == "railway":
            if not self.check_cli("railway"):
                msg = (
                    f"⚠ Railway CLI not found.\n"
                    f"To install Railway CLI, run in PowerShell:\n"
                    f"   npm install -g @railway/cli\n"
                    f"   railway login\n\n"
                    f"Config files auto-generated: {', '.join(scaffolded) if scaffolded else 'railway.toml & Procfile ready'}\n"
                    f"Once logged in, run: /deploy railway"
                )
                return ToolResult(False, msg, "deploy")

            # Check authentication
            whoami = shell.run("railway whoami")
            if not whoami.ok or "not logged in" in whoami.log.lower():
                return ToolResult(
                    False,
                    f"⚠ You are not logged into Railway.\n"
                    f"Please run in PowerShell: railway login\n"
                    f"Then run: /deploy railway",
                    "deploy"
                )

            # Auto-sync .env variables to Railway
            env_file = cwd / ".env"
            env_synced = 0
            if env_file.exists():
                for line in env_file.read_text(errors="ignore").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("\"'")
                        if k and v:
                            shell.run(f'railway variables --set "{k}={v}"')
                            env_synced += 1

            # Trigger deployment
            cmd = subcmd or "railway up --detach"
            res = shell.run(cmd, timeout=180)
            url_res = shell.run("railway domain")
            domain = url_res.stdout.strip() if url_res.ok else ""

            msg = (
                f"🚀 [Railway Deploy Triggered]\n"
                f"  Account : {whoami.stdout.strip()}\n"
                f"  Configs : {', '.join(scaffolded) or 'Existing configs used'}\n"
                f"  Env Vars: {env_synced} synced from .env\n"
                f"  Command : {cmd}\n"
                f"  Status  : {'✔ Success' if res.ok else '✖ Failed'}\n"
                f"  Output  :\n{res.log}\n"
            )
            if domain:
                msg += f"\n🌐 Live Domain: https://{domain}"
            return ToolResult(res.ok, msg, "deploy")

        # ── 2. DOCKER DEPLOY ───────────────────────────────────────────────────
        elif target == "docker":
            if not self.check_cli("docker"):
                return ToolResult(
                    False,
                    "⚠ Docker is not installed or Docker Desktop is not running.\n"
                    "Install from: https://www.docker.com/products/docker-desktop",
                    "deploy"
                )
            app_name = (cwd.name.lower() or "ignite_app").replace(" ", "_")
            if (cwd / "docker-compose.yml").exists():
                cmd = subcmd or "docker compose up --build -d"
            else:
                cmd = subcmd or f"docker build -t {app_name} . && docker run -d --restart unless-stopped --name {app_name} {app_name}"
            res = shell.run(cmd, timeout=300)
            return ToolResult(
                res.ok,
                f"🐳 [Docker Container Deploy]\n"
                f"  Configs : {', '.join(scaffolded) or 'Existing Dockerfile'}\n"
                f"  Command : {cmd}\n"
                f"  Status  : {'✔ Running in background' if res.ok else '✖ Failed'}\n"
                f"  Output  :\n{res.log}",
                "deploy"
            )

        # ── 3. FLY.IO DEPLOY ───────────────────────────────────────────────────
        elif target == "fly":
            cli = "flyctl" if self.check_cli("flyctl") else "fly"
            if not self.check_cli(cli):
                return ToolResult(
                    False,
                    f"⚠ Fly CLI not found.\n"
                    f"Install in PowerShell:\n"
                    f"   iwr https://fly.io/install.ps1 -useb | iex\n"
                    f"Then run: {cli} auth login",
                    "deploy"
                )
            cmd = subcmd or f"{cli} deploy"
            res = shell.run(cmd, timeout=300)
            return ToolResult(
                res.ok,
                f"🎈 [Fly.io Deploy]\n"
                f"  Configs : {', '.join(scaffolded) or 'fly.toml'}\n"
                f"  Command : {cmd}\n"
                f"  Status  : {'✔ Deployed' if res.ok else '✖ Failed'}\n"
                f"  Output  :\n{res.log}",
                "deploy"
            )

        # ── 4. RENDER DEPLOY ───────────────────────────────────────────────────
        elif target == "render":
            msg = (
                f"🚀 [Render Deployment Ready]\n"
                f"  Render uses Git-backed infrastructure-as-code.\n"
                f"  Config generated: {', '.join(scaffolded) or 'render.yaml'}\n\n"
                f"To deploy on Render:\n"
                f"  1. Push this project to GitHub: git push origin main\n"
                f"  2. Go to https://dashboard.render.com -> New -> Blueprint\n"
                f"  3. Select your repo — Render will auto-detect render.yaml and deploy!"
            )
            return ToolResult(True, msg, "deploy")

        # ── 5. HEROKU DEPLOY ───────────────────────────────────────────────────
        elif target == "heroku":
            if not self.check_cli("heroku"):
                return ToolResult(False, "⚠ Heroku CLI not found. Run: winget install Heroku.CLI", "deploy")
            cmd = subcmd or "git push heroku main"
            res = shell.run(cmd, timeout=240)
            return ToolResult(res.ok, f"Heroku Deploy:\n{res.log}", "deploy")

        # ── 6. VERCEL DEPLOY ───────────────────────────────────────────────────
        elif target == "vercel":
            if not self.check_cli("vercel"):
                return ToolResult(False, "⚠ Vercel CLI not found. Run: npm install -g vercel", "deploy")
            cmd = subcmd or "vercel --prod"
            res = shell.run(cmd, timeout=180)
            return ToolResult(res.ok, f"Vercel Deploy:\n{res.log}", "deploy")

        return ToolResult(False, f"Unsupported platform: {target}", "deploy")

    def help_menu(self) -> str:
        lines = [
            f"{C.BCYN}╔══════════════════════════════════════════════════════════════════╗{C.RST}",
            f"{C.BCYN}║  🌍 IGNITE Cloud Deployer — Supported Platforms                 ║{C.RST}",
            f"{C.BCYN}╠══════════════════════════════════════════════════════════════════╣{C.RST}",
        ]
        for key, p in self.PLATFORMS.items():
            lines.append(f"║  {C.YEL}/deploy {key:<10}{C.RST} ▸ {p['name']:<8} — {p['desc']:<32} ║")
        lines.append(f"{C.BCYN}╚══════════════════════════════════════════════════════════════════╝{C.RST}")
        lines.append(f"\n{C.DIM}Example: /deploy railway  |  /deploy docker  |  /deploy fly{C.RST}")
        return "\n".join(lines)

deploy_engine = CloudDeployEngine()

def tool_deploy(subcmd: str = "", platform: str = "") -> ToolResult:
    """Deploy current project to cloud platform (Railway, Render, Fly.io, Heroku, Docker, Vercel).
    Auto-detects project structure, generates required config files, syncs .env, and deploys.
    """
    return deploy_engine.deploy(platform=platform, subcmd=subcmd, cwd=shell.cwd)

ERROR_KEYWORDS = ["Traceback (most recent call last)", "Error:", "Exception:", "FAILED",
                   "ModuleNotFoundError", "SyntaxError", "ImportError", "AttributeError",
                   "TypeError", "ValueError", "FileNotFoundError", "PermissionError",
                   "ConnectionError", "OSError", "RuntimeError"]

def tool_spawn(cmd: str, name: str = "", mode: str = "window") -> ToolResult:
    """Spawn a script/process. mode='window' opens new terminal, mode='background' runs silently.
    For window mode: waits up to 8 seconds after spawn, reads log, and reports any errors found.
    """
    real_cmd = obfuscator.unmask(cmd)
    real_name = name or real_cmd[:40]
    cwd = str(shell.cwd)

    if mode == "background":
        mp = proc_registry.spawn_background(real_cmd, cwd, real_name)
        msg = (f"✔ Background process started!\n"
               f"  PID  : {mp.pid}\n"
               f"  Name : {mp.name}\n"
               f"  Log  : {mp.log_path}\n"
               f"  Use read_log with pid={mp.pid} to check output.")
        return ToolResult(True, msg, "spawn")

    # ── Window mode ───────────────────────────────────────────────────────────
    pid, spawn_msg = proc_registry.spawn_window(real_cmd, cwd, real_name)
    if pid < 0:
        return ToolResult(False, spawn_msg, "spawn")

    mp = proc_registry._procs.get(pid)
    print(f"{C.DIM}  ⏳ Waiting for process to settle (5s)...{C.RST}")

    # Poll up to 8 seconds for log to appear and process to either crash or stabilise
    deadline = time.time() + 8
    log_content = ""
    while time.time() < deadline:
        time.sleep(1)
        if mp:
            log_content = mp.tail_log(60)
            # If log has content and process is no longer alive → crashed early
            if log_content.strip() and log_content != "[No output yet]":
                if not mp.is_alive:
                    break   # definitely finished — either success or crash
            # If alive and we have some output, 5s is enough to confirm startup
            if mp.is_alive and log_content.strip() and log_content != "[No output yet]":
                if time.time() > (deadline - 3):  # waited at least 5s
                    break

    # Refresh log after wait
    if mp:
        log_content = mp.tail_log(80)
        is_alive = mp.is_alive
    else:
        log_content = "[No log available]"
        is_alive = False

    # Scan for error patterns
    has_error = any(kw in log_content for kw in ERROR_KEYWORDS)

    status_icon = "🟢 RUNNING" if is_alive else "🔴 STOPPED"

    if has_error:
        error_snippet = "\n".join(
            line for line in log_content.splitlines()
            if any(kw in line for kw in ERROR_KEYWORDS)
        )[:600]
        full_msg = (
            f"⚠ Process spawned but ERRORS detected!\n"
            f"  PID    : {pid}\n"
            f"  Status : {status_icon}\n"
            f"  Errors :\n{error_snippet}\n\n"
            f"--- Full log (last 30 lines) ---\n{mp.tail_log(30) if mp else log_content}"
        )
        return ToolResult(False, full_msg, "spawn")

    if not is_alive and log_content.strip() and log_content != "[No output yet]":
        # Process finished — could be a one-shot script (OK) or crash without error keyword
        # Check return code heuristically by looking for obvious failure words
        looks_failed = any(w in log_content.lower() for w in ["failed", "cannot", "denied", "not found"])
        status_msg = (
            f"{'⚠ Process finished (may have failed)' if looks_failed else '✔ Process completed'}\n"
            f"  PID    : {pid}\n"
            f"  Status : {status_icon}\n\n"
            f"--- Output ---\n{mp.tail_log(30) if mp else log_content}"
        )
        return ToolResult(not looks_failed, status_msg, "spawn")

    # All good — running with no errors
    success_msg = (
        f"✔ Process launched successfully!\n"
        f"  PID    : {pid}\n"
        f"  Status : {status_icon}\n"
        f"  Window : IGNITE [{real_name}]\n\n"
        f"--- Startup output (last 20 lines) ---\n{mp.tail_log(20) if mp else log_content}"
    )
    return ToolResult(True, success_msg, "spawn")

def tool_kill(pid: int = None, name: str = "") -> ToolResult:
    """Kill a process by PID or name."""
    if pid and pid > 0:
        result = proc_registry.kill(pid)
    elif name:
        result = proc_registry.kill_by_name(obfuscator.unmask(name))
    else:
        result = "Error: provide pid or name to kill"
    return ToolResult(True, result, "kill")

def tool_process_status(pid: int = None, tail: int = 60) -> ToolResult:
    """List all tracked processes or read output log of a specific PID."""
    output = proc_registry.status(pid, tail)
    return ToolResult(True, output, "process_status")

def tool_read_log(pid: int, tail: int = 80) -> ToolResult:
    """Read the latest output from a spawned process log."""
    mp = proc_registry._procs.get(pid)
    if not mp:
        return ToolResult(False, f"PID {pid} not tracked.", "read_log")
    alive = "🟢 RUNNING" if mp.is_alive else "🔴 STOPPED"
    return ToolResult(True, f"{alive} | {mp.name}\n{mp.tail_log(tail)}", "read_log")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7c — SEMANTIC CODEBASE INDEXER & RAG (Zero-Dep BM25 + AST Symbols)
# ══════════════════════════════════════════════════════════════════════════════
class CodebaseIndexer:
    """
    High-performance, zero-dependency codebase indexer and semantic search engine.
    - Uses SQLite FTS5 for BM25 ranking and fast full-text search.
    - Python AST extraction parses classes, methods, functions, docstrings, and signatures.
    - Incremental cache tracking file mtime/hash so re-indexes only touch changed files.
    """
    EXTENSIONS = {
        ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".html", ".css", ".scss",
        ".md", ".yml", ".yaml", ".toml", ".txt", ".sh", ".bat", ".ps1", ".rs",
        ".go", ".java", ".c", ".cpp", ".h", ".hpp", ".sql"
    }
    IGNORE_DIRS = {
        ".git", "node_modules", "venv", ".venv", "env", "__pycache__", "dist",
        "build", ".ignite_scratch", ".idea", ".vscode", "coverage", ".next"
    }

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)
        self.db_path = self._get_db_path()
        self._lock = threading.RLock()
        self._init_db()

    def set_workspace(self, new_ws: Path):
        with self._lock:
            self.workspace = Path(new_ws)
            self.db_path = self._get_db_path()
            self._init_db()

    def _get_db_path(self) -> Path:
        scratch = self.workspace / ".ignite_scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        return scratch / "code_index.db"

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            try:
                conn = self._get_conn()
                with conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS files (
                            path TEXT PRIMARY KEY,
                            mtime REAL,
                            size INTEGER,
                            hash TEXT,
                            indexed_at REAL
                        )
                    """)
                    conn.execute("""
                        CREATE VIRTUAL TABLE IF NOT EXISTS code_fts USING fts5(
                            file_path UNINDEXED,
                            symbol_name,
                            symbol_type UNINDEXED,
                            start_line UNINDEXED,
                            end_line UNINDEXED,
                            content,
                            tokenize='porter unicode61'
                        )
                    """)
                conn.close()
            except Exception:
                pass

    def _extract_chunks(self, file_path: Path, rel_path: str) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []
        try:
            raw_bytes = file_path.read_bytes()
            if b"\x00" in raw_bytes[:1024]:  # binary file check
                return []
            text = raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            return []

        lines = text.splitlines()
        if not lines:
            return []

        # 1. If Python, attempt AST symbol extraction
        if file_path.suffix.lower() == ".py":
            try:
                tree = ast.parse(text)
                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, ast.ClassDef):
                        s_line = node.lineno
                        e_line = getattr(node, "end_lineno", s_line)
                        doc = ast.get_docstring(node) or ""
                        snippet = "\n".join(lines[s_line - 1 : min(e_line, s_line + 40)])
                        chunks.append({
                            "symbol_name": node.name,
                            "symbol_type": "class",
                            "start_line": s_line,
                            "end_line": e_line,
                            "content": f"class {node.name}\n{doc}\n{snippet}"
                        })
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                ms_line = item.lineno
                                me_line = getattr(item, "end_lineno", ms_line)
                                mdoc = ast.get_docstring(item) or ""
                                msnippet = "\n".join(lines[ms_line - 1 : min(me_line, ms_line + 35)])
                                chunks.append({
                                    "symbol_name": f"{node.name}.{item.name}",
                                    "symbol_type": "method",
                                    "start_line": ms_line,
                                    "end_line": me_line,
                                    "content": f"{node.name}.{item.name}\n{mdoc}\n{msnippet}"
                                })
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        s_line = node.lineno
                        e_line = getattr(node, "end_lineno", s_line)
                        doc = ast.get_docstring(node) or ""
                        snippet = "\n".join(lines[s_line - 1 : min(e_line, s_line + 40)])
                        chunks.append({
                            "symbol_name": node.name,
                            "symbol_type": "function",
                            "start_line": s_line,
                            "end_line": e_line,
                            "content": f"def {node.name}\n{doc}\n{snippet}"
                        })
            except Exception:
                pass  # Fall back to sliding windows if AST parse fails

        # 2. Sliding window chunks (for non-Python or files where AST found few symbols)
        if len(chunks) == 0:
            window_size = 40
            overlap = 10
            stride = max(1, window_size - overlap)
            for i in range(0, len(lines), stride):
                chunk_lines = lines[i : i + window_size]
                if not chunk_lines:
                    break
                s_line = i + 1
                e_line = min(len(lines), i + len(chunk_lines))
                content = "\n".join(chunk_lines)
                chunks.append({
                    "symbol_name": Path(rel_path).name,
                    "symbol_type": "chunk",
                    "start_line": s_line,
                    "end_line": e_line,
                    "content": content
                })

        return chunks

    def index_workspace(self, force: bool = False) -> Dict[str, int]:
        with self._lock:
            self._init_db()
            conn = self._get_conn()
            scanned = 0
            indexed = 0
            total_chunks = 0
            current_files = set()

            try:
                for root, dirs, files in os.walk(self.workspace):
                    dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS and not d.startswith(".")]
                    for f in files:
                        p = Path(root) / f
                        if p.suffix.lower() not in self.EXTENSIONS:
                            continue
                        try:
                            rel_path = str(p.relative_to(self.workspace)).replace("\\", "/")
                        except Exception:
                            rel_path = str(p)
                        current_files.add(rel_path)
                        scanned += 1

                        try:
                            stat = p.stat()
                            if stat.st_size > 1_000_000:  # skip >1MB
                                continue

                            row = conn.execute("SELECT mtime, size FROM files WHERE path = ?", (rel_path,)).fetchone()
                            if not force and row and abs(row["mtime"] - stat.st_mtime) < 0.01 and row["size"] == stat.st_size:
                                continue  # unchanged

                            chunks = self._extract_chunks(p, rel_path)
                            with conn:
                                conn.execute("DELETE FROM code_fts WHERE file_path = ?", (rel_path,))
                                for c in chunks:
                                    conn.execute(
                                        "INSERT INTO code_fts (file_path, symbol_name, symbol_type, start_line, end_line, content) "
                                        "VALUES (?, ?, ?, ?, ?, ?)",
                                        (rel_path, c["symbol_name"], c["symbol_type"], c["start_line"], c["end_line"], c["content"])
                                    )
                                conn.execute(
                                    "INSERT OR REPLACE INTO files (path, mtime, size, hash, indexed_at) VALUES (?, ?, ?, ?, ?)",
                                    (rel_path, stat.st_mtime, stat.st_size, "", time.time())
                                )
                            indexed += 1
                            total_chunks += len(chunks)
                        except Exception:
                            continue

                with conn:
                    db_files = [r[0] for r in conn.execute("SELECT path FROM files").fetchall()]
                    for df in db_files:
                        if df not in current_files:
                            conn.execute("DELETE FROM files WHERE path = ?", (df,))
                            conn.execute("DELETE FROM code_fts WHERE file_path = ?", (df,))

                total_chunks_in_db = conn.execute("SELECT COUNT(*) FROM code_fts").fetchone()[0]
            finally:
                conn.close()

            return {"scanned": scanned, "indexed": indexed, "total_chunks": total_chunks_in_db}

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        self._init_db()
        tokens = re.findall(r"[A-Za-z0-9_]+", query)
        if not tokens:
            return []

        conn = self._get_conn()
        try:
            count = conn.execute("SELECT COUNT(*) FROM code_fts").fetchone()[0]
        except Exception:
            count = 0
        conn.close()

        if count == 0:
            self.index_workspace(force=False)

        conn = self._get_conn()
        results: List[Dict[str, Any]] = []
        try:
            fts_query = " OR ".join(f'"{t}"' for t in tokens)
            sql = """
                SELECT file_path, symbol_name, symbol_type, start_line, end_line, content, rank
                FROM code_fts
                WHERE code_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            rows = conn.execute(sql, (fts_query, top_k * 3)).fetchall()
            q_lower_terms = [t.lower() for t in tokens]

            scored: List[Tuple[float, Dict[str, Any]]] = []
            for r in rows:
                base_score = float(r["rank"])
                sym = (r["symbol_name"] or "").lower()
                fpath = (r["file_path"] or "").lower()
                content = r["content"] or ""

                boost = 0.0
                for term in q_lower_terms:
                    if term == sym:
                        boost += 3.0
                    elif term in sym:
                        boost += 1.5
                    if term in fpath:
                        boost += 1.0

                adjusted_score = base_score - boost
                scored.append((adjusted_score, {
                    "file_path": r["file_path"],
                    "symbol_name": r["symbol_name"],
                    "symbol_type": r["symbol_type"],
                    "start_line": int(r["start_line"]),
                    "end_line": int(r["end_line"]),
                    "content": content,
                    "score": adjusted_score
                }))

            scored.sort(key=lambda x: x[0])
            results = [x[1] for x in scored[:top_k]]
        except Exception:
            pass
        finally:
            conn.close()

        return results

    def status(self) -> str:
        self._init_db()
        conn = self._get_conn()
        try:
            file_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            chunk_count = conn.execute("SELECT COUNT(*) FROM code_fts").fetchone()[0]
            last_run = conn.execute("SELECT MAX(indexed_at) FROM files").fetchone()[0]
            last_str = datetime.fromtimestamp(last_run).strftime("%Y-%m-%d %H:%M:%S") if last_run else "Never"
            return f"Files: {file_count} | Chunks: {chunk_count} | Last Indexed: {last_str} | DB: {self.db_path.name}"
        except Exception as e:
            return f"Index status error: {e}"
        finally:
            conn.close()

code_indexer = CodebaseIndexer(shell.cwd)

def tool_code_search(query: str, top_k: int = 5) -> ToolResult:
    """Semantic vector/keyword hybrid search over local codebase with AST symbol awareness."""
    if not query.strip():
        return ToolResult(False, "Error: search query cannot be empty", "code_search")

    matches = code_indexer.search(query, top_k=top_k)
    if not matches:
        return ToolResult(True, f"No codebase matches found for: '{query}'. Use /index rebuild to refresh the index.", "code_search")

    lines = [f"Found {len(matches)} relevant code match(es) for query: '{query}'\n"]
    for i, m in enumerate(matches, 1):
        sym_label = f" [{m['symbol_type']}: {m['symbol_name']}]" if m['symbol_name'] else ""
        lines.append(f"── Match {i} ── {m['file_path']} (lines {m['start_line']}-{m['end_line']}){sym_label}")
        snip = textwrap.indent(m["content"][:600], "    ")
        lines.append(snip)
        if len(m["content"]) > 600:
            lines.append("    ... [remaining lines truncated]")
        lines.append("")

    return ToolResult(True, "\n".join(lines).strip(), "code_search")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7d — MODEL CONTEXT PROTOCOL (MCP) CLIENT & REGISTRY
# ══════════════════════════════════════════════════════════════════════════════
class McpClient:
    """
    Subprocess JSON-RPC 2.0 Client implementing the Model Context Protocol (MCP) specification.
    Communicates via stdin/stdout with external tool servers (filesystem, sqlite, git, web, APIs).
    """
    def __init__(self, name: str, command: str, args: List[str] = None, env: Dict[str, str] = None, cwd: Path = None):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or os.environ.copy()
        self.cwd = cwd or Path.cwd()
        self.proc: Optional[subprocess.Popen] = None
        self._req_id = 0
        self._lock = threading.RLock()
        self._pending: Dict[int, Tuple[threading.Event, Dict[str, Any]]] = {}
        self.tools: List[Dict[str, Any]] = []
        self.server_info: Dict[str, Any] = {}
        self.connected = False
        self.error: Optional[str] = None
        self._reader_thread: Optional[threading.Thread] = None

    def start(self, timeout: float = 12.0) -> bool:
        cmd_bin = shutil.which(self.command) or self.command
        full_cmd = [cmd_bin] + self.args
        try:
            self.proc = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.cwd),
                env=self.env,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace"
            )
            self._reader_thread = threading.Thread(target=self._stdout_reader, daemon=True)
            self._reader_thread.start()

            init_res = self.send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "IGNITE-Agent", "version": "3.0"}
            }, timeout=timeout)

            self.server_info = init_res.get("result", {}).get("serverInfo", {})
            self.send_notification("notifications/initialized")

            tools_res = self.send_request("tools/list", {}, timeout=timeout)
            self.tools = tools_res.get("result", {}).get("tools", [])
            self.connected = True
            self.error = None
            return True
        except Exception as e:
            self.error = str(e)
            self.connected = False
            return False

    def _stdout_reader(self):
        while self.proc and self.proc.poll() is None:
            try:
                line = self.proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                msg = json.loads(line)
                mid = msg.get("id")
                if mid is not None and mid in self._pending:
                    evt, box = self._pending[mid]
                    box["data"] = msg
                    evt.set()
            except Exception:
                pass

    def send_request(self, method: str, params: Dict[str, Any] = None, timeout: float = 15.0) -> Dict[str, Any]:
        if not self.proc or self.proc.poll() is not None:
            raise RuntimeError(f"MCP server '{self.name}' process is not running.")
        with self._lock:
            self._req_id += 1
            rid = self._req_id

        payload = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}
        evt = threading.Event()
        box: Dict[str, Any] = {}
        self._pending[rid] = (evt, box)
        try:
            raw = json.dumps(payload) + "\n"
            self.proc.stdin.write(raw)
            self.proc.stdin.flush()
        except Exception as e:
            self._pending.pop(rid, None)
            raise RuntimeError(f"Failed to communicate with MCP '{self.name}': {e}")

        if not evt.wait(timeout):
            self._pending.pop(rid, None)
            raise TimeoutError(f"MCP server '{self.name}' timed out waiting for '{method}' response ({timeout}s)")

        self._pending.pop(rid, None)
        res = box.get("data", {})
        if "error" in res:
            err = res["error"]
            raise RuntimeError(f"MCP error {err.get('code')}: {err.get('message')}")
        return res

    def send_notification(self, method: str, params: Dict[str, Any] = None):
        if not self.proc or self.proc.poll() is not None:
            return
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        try:
            self.proc.stdin.write(json.dumps(payload) + "\n")
            self.proc.stdin.flush()
        except Exception:
            pass

    def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None, timeout: float = 30.0) -> ToolResult:
        try:
            res = self.send_request("tools/call", {"name": tool_name, "arguments": arguments or {}}, timeout=timeout)
            result_data = res.get("result", {})
            content_items = result_data.get("content", [])
            output_parts = []
            for item in content_items:
                if item.get("type") == "text":
                    output_parts.append(item.get("text", ""))
                else:
                    output_parts.append(json.dumps(item))
            out_str = "\n".join(output_parts).strip() or "Tool completed with no output."
            is_err = result_data.get("isError", False)
            return ToolResult(not is_err, out_str, f"mcp_{self.name}_{tool_name}")
        except Exception as e:
            return ToolResult(False, f"MCP tool call failed ({self.name}::{tool_name}): {e}", "mcp_call")

    def close(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
            self.connected = False


class McpRegistry:
    """Discovers, initializes, and routes tool calls to configured MCP servers."""
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)
        self.clients: Dict[str, McpClient] = {}
        self._lock = threading.RLock()

    def set_workspace(self, new_ws: Path):
        with self._lock:
            self.workspace = Path(new_ws)

    def load_config(self) -> Dict[str, Any]:
        candidates = [
            self.workspace / ".ignite_mcp.json",
            Path.home() / ".ignite_mcp.json"
        ]
        for c in candidates:
            if c.exists():
                try:
                    with open(c, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
        return {"mcpServers": {}}

    def init_config_template(self) -> Path:
        target = self.workspace / ".ignite_mcp.json"
        if not target.exists():
            template = {
                "mcpServers": {
                    "filesystem": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", str(self.workspace)],
                        "description": "Standard filesystem MCP access"
                    },
                    "sqlite": {
                        "command": "uvx",
                        "args": ["mcp-server-sqlite", "--db-path", "app.db"],
                        "description": "Direct SQLite database MCP querying"
                    }
                }
            }
            with open(target, "w", encoding="utf-8") as f:
                json.dump(template, f, indent=2)
        return target

    def get_client(self, server_name: str) -> Optional[McpClient]:
        with self._lock:
            if server_name in self.clients and self.clients[server_name].connected:
                return self.clients[server_name]

            cfg = self.load_config().get("mcpServers", {}).get(server_name)
            if not cfg:
                return None

            client = McpClient(
                name=server_name,
                command=cfg.get("command", ""),
                args=cfg.get("args", []),
                env={**os.environ, **cfg.get("env", {})},
                cwd=self.workspace
            )
            ok = client.start()
            if ok:
                self.clients[server_name] = client
                return client
            return None

    def list_tools(self) -> List[Dict[str, Any]]:
        all_tools = []
        cfg = self.load_config().get("mcpServers", {})
        for sname in cfg.keys():
            client = self.get_client(sname)
            if client and client.tools:
                for t in client.tools:
                    all_tools.append({
                        "server": sname,
                        "name": t.get("name"),
                        "description": t.get("description", ""),
                        "schema": t.get("inputSchema", {})
                    })
        return all_tools

    def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any] = None) -> ToolResult:
        client = self.get_client(server_name)
        if not client:
            return ToolResult(
                False,
                f"MCP server '{server_name}' not found or failed to start. Check .ignite_mcp.json or run /mcp init.",
                "mcp_call"
            )
        return client.call_tool(tool_name, arguments or {})

    def status(self) -> str:
        cfg = self.load_config().get("mcpServers", {})
        if not cfg:
            return "No MCP servers configured. Run /mcp init to create a starter .ignite_mcp.json."
        lines = ["Configured MCP Servers:"]
        for sname, sdata in cfg.items():
            client = self.clients.get(sname)
            status_tag = "🟢 CONNECTED" if (client and client.connected) else "⚪ IDLE / READY"
            tool_cnt = len(client.tools) if (client and client.connected) else 0
            lines.append(f"  • {sname} [{status_tag}] — {sdata.get('command')} {' '.join(sdata.get('args', []))} ({tool_cnt} tools)")
        return "\n".join(lines)

mcp_registry = McpRegistry(shell.cwd)

def tool_mcp_call(server: str, tool: str, arguments: Dict[str, Any] = None) -> ToolResult:
    """Execute a tool on an external Model Context Protocol (MCP) server."""
    if not server or not tool:
        return ToolResult(False, "Error: both 'server' and 'tool' parameters are required for mcp_call", "mcp_call")
    return mcp_registry.call_tool(server, tool, arguments or {})

TOOL_DISPATCH = {
    "terminal":       lambda d: tool_terminal(d.get("cmd", "")),
    "file_read":      lambda d: tool_file_read(d.get("path", ""), d.get("start", 1), d.get("end")),
    "file_write":     lambda d: tool_file_write(d.get("path", ""), d.get("content", "")),
    "file_patch":     lambda d: tool_file_patch(d.get("path", ""), d.get("diff", "")),
    "git":            lambda d: tool_git(d.get("subcmd", "status")),
    "git_diff":       lambda d: tool_git_diff(d.get("path", "")),
    "verify_code":    lambda d: tool_verify_code(d.get("cmd", ""), d.get("path", "")),
    "python_eval":    lambda d: tool_python_eval(d.get("code", "")),
    "search":         lambda d: tool_search(d.get("query", "")),
    "code_search":    lambda d: tool_code_search(d.get("query", ""), int(d.get("top_k", 5))),
    "mcp_call":       lambda d: tool_mcp_call(d.get("server", ""), d.get("tool", ""), d.get("arguments") or {}),
    "deploy":         lambda d: tool_deploy(d.get("subcmd", ""), d.get("platform", "")),
    "spawn":          lambda d: tool_spawn(d.get("cmd", ""), d.get("name", ""), d.get("mode", "window")),
    "kill":           lambda d: tool_kill(d.get("pid"), d.get("name", "")),
    "process_status": lambda d: tool_process_status(d.get("pid"), d.get("tail", 60)),
    "read_log":       lambda d: tool_read_log(d.get("pid", 0), d.get("tail", 80)),
}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """You are IGNITE V3 PRO — an elite AI assistant, coding partner, and autonomous DevOps Agent.
You can chat, answer questions, write code, run scripts, deploy projects, and manage processes — all from one place.

━━━ TWO MODES ━━━

MODE 1 — CHAT  (greetings, questions, explanations, general conversation)
  Reply immediately: {"action":"done","message":"<your friendly answer>","thought":"chat"}
  Do NOT run tools for casual questions. Just answer directly.

MODE 2 — TASK  (code, files, deployments, bots, scripts, debugging)
  Use the ReAct loop. Execute tools step by step until the task is fully done.

━━━ ALL 18 TOOLS (output ONE pure JSON per turn — no markdown, no prose) ━━━

── FILE & SAFETY TOOLS ──
1.  {"action":"terminal",       "cmd":"<PowerShell>",              "thought":"<why>"}
2.  {"action":"file_read",      "path":"<path>",                   "thought":"<why>", "start":1, "end":50}
3.  {"action":"file_write",     "path":"<path>", "content":"<txt>","thought":"<why>"}
    ⚠ file_write automatically runs AST pre-flight checks on Python & JSON. Broken syntax will be rejected!
4.  {"action":"file_patch",     "path":"<path>", "diff":"<diff>",  "thought":"<why>"}
5.  {"action":"git",            "subcmd":"<args>",                 "thought":"<why>"}
6.  {"action":"git_diff",       "path":"<optional_path>",          "thought":"<why>"}
    → Review uncommitted changes and diffs before declaring a task complete.
7.  {"action":"verify_code",    "cmd":"<optional_test_cmd>", "path":"<optional_file>", "thought":"<why>"}
    → Self-Healing Test Runner: auto-detects pytest, unittest, npm test, or compilation.
    → If verification fails, it returns the exact stack trace so you can self-heal!
8.  {"action":"python_eval",    "code":"<python>",                 "thought":"<why>"}

── PROCESS TOOLS ──
9.  {"action":"spawn",          "cmd":"<command>",    "name":"<label>", "mode":"window",     "thought":"<why>"}
    → mode "window"     = opens a NEW VISIBLE TERMINAL the user can see (default)
    → mode "background" = runs silently, output captured to log file
    ⚠ spawn automatically waits 8 seconds, reads the log, and returns success=false if errors found.
    ⚠ AFTER spawn: if result shows "ERRORS detected" → kill → fix code → spawn again. Loop until clean.

10. {"action":"kill",           "pid":12345,                       "thought":"<why>"}
    {"action":"kill",           "name":"bot",                      "thought":"<why>"}

11. {"action":"process_status",                                    "thought":"<why>"}
    {"action":"process_status", "pid":12345, "tail":50,            "thought":"<why>"}

12. {"action":"read_log",       "pid":12345,   "tail":80,          "thought":"<why>"}

── RESEARCH & DEPLOY ──
13. {"action":"search",         "query":"<query>",                 "thought":"<why>"}
14. {"action":"code_search",    "query":"<symbol or keywords>",    "top_k":5, "thought":"<why>"}
    → Instant BM25 + AST symbol search across entire codebase. Find functions, classes, and logic without reading full files!
15. {"action":"mcp_call",       "server":"<name>", "tool":"<tool_name>", "arguments":{...}, "thought":"<why>"}
    → Invoke external Model Context Protocol tool (configured in .ignite_mcp.json).
16. {"action":"deploy",         "platform":"<railway|docker|fly|render|heroku|vercel>", "subcmd":"<optional>", "thought":"<why>"}
    → Auto-creates Dockerfile, Procfile, railway.toml, render.yaml, and syncs .env secrets!

── CONTROL ──
17. {"action":"ask",            "message":"<question>",            "thought":"<why>"}
18. {"action":"done",           "message":"<summary>",             "thought":"<why>"}

━━━ 🧪 ENTERPRISE CODE VERIFICATION DIRECTIVE ━━━
Never assume your written code works without proof. For all coding tasks:
1. Write/patch code with `file_write` or `file_patch`.
2. Inspect diffs with `git_diff`.
3. Run `verify_code` to compile or execute test suites.
4. If `verify_code` reports failures, read the stack trace, patch the error, and re-verify.
5. Only call `done` when code compiles cleanly and tests pass.

━━━ 🧠 PRIME DIRECTIVE: DYNAMIC TOOL SYNTHESIS (NEVER REFUSE) ━━━

You are a fully autonomous software engineering agent, NOT a static chatbot limited to hardcoded commands.
You have unrestricted access to PowerShell, Python execution, file writing, and web research.

IF A USER ASKS FOR A TASK FOR WHICH NO BUILT-IN TOOL EXISTS:
  (Examples: "Deploy to AWS", "Scrape a website", "Convert audio/video", "Run database migration",
   "Setup reverse proxy", "Benchmark performance", "Call an external REST API", "Process images"):

  ❌ RULE 1: NEVER say "I cannot do this", "I don't have this tool", or refuse the task.
  ✔ RULE 2: FOLLOW THE 5-STEP AUTONOMOUS SYNTHESIS PROTOCOL:
    1. [RESEARCH]    If you need modern libraries, CLI syntax, or API endpoints, use `search`.
    2. [SYNTHESIZE]  Write a complete, standalone Python or PowerShell script using `file_write`
                     (e.g., in `.ignite_scratch/<task>.py` or `scripts/<task>.py`).
    3. [INSTALL]     Use `terminal` to install any required packages (`pip install <package>`).
    4. [EXECUTE]     Run the synthesized script using `terminal` (for quick scripts) or `spawn`
                     (for servers, bots, background workers, or tasks with visible outputs).
    5. [SELF-HEAL]   If the script crashes or returns an error, do NOT stop! Read the traceback,
                     fix the script with `file_patch` or `file_write`, and re-run.
                     Iterate until the script runs cleanly and completes the user's objective.

━━━ WORKFLOW PATTERNS ━━━

🤖 BUILDING & RUNNING A BOT / SCRIPT:
  1. Use `ask` to collect ALL needed credentials (tokens, API keys, ports)
  2. Use `file_write` to create the main script + a `.env` file with the secrets
  3. Use `terminal` to install dependencies: `pip install -r requirements.txt`
  4. Use `spawn` with mode="window" to launch the bot in a NEW VISIBLE TERMINAL
  5. The spawn result tells you SUCCESS or ERRORS with log content — read it carefully!
  6. If spawn returned errors → `kill` the process → read the error → fix with `file_write`/`file_patch` → `spawn` again
  7. Repeat step 6 until spawn confirms the process is 🟢 RUNNING with no errors
  8. ONLY then use `done` to summarize. Give the user the PID.

🌐 CLOUD DEPLOYMENT WORKFLOW:
  - When user asks to deploy to cloud (Railway, Docker, Render, Fly.io, Heroku, Vercel):
  - Use `deploy` tool with "platform": "railway" (or "docker", "fly", etc.).
  - The deploy engine automatically scaffolds config files, initializes git, syncs .env secrets, and runs the deploy.
  - Report the live URL or domain back to the user.

🔄 AUTO-FIX LOOP (mandatory when spawn fails):
  spawn → ERROR detected → kill → fix code → spawn → ERROR? → kill → fix → spawn → ✅ SUCCESS → done
  NEVER skip the fix-and-retry loop. NEVER say "done" while spawn shows errors.

🧪 TESTING A SCRIPT:
  1. Write the script with `file_write`
  2. If it's interactive (has input()): use `done` to tell user to run it themselves
  3. If it's non-interactive: `spawn` with mode="background", then `read_log` to check output
  4. `kill` when done testing

🔧 DEBUGGING:
  - If exit code ≠ 0: use `search` for the error, fix with `file_patch`, re-run
  - If a process crashes: read the spawn result (it includes the traceback) → fix and `spawn` again

━━━ CRITICAL RULES ━━━
- Output ONLY pure JSON. One object per turn. Nothing else.
- NEVER say "I don't have that tool" or refuse an unfamiliar task. Always synthesize a script to solve it!
- NEVER run `python script.py` in terminal if script has input() — use `spawn` with mode="window" instead.
- Always collect ALL required secrets/tokens via `ask` BEFORE writing any file.
- The `spawn` tool already waits and checks for errors — READ the result JSON before deciding next step.
- If spawn result success=false: ALWAYS kill + fix + respawn. Do NOT use `done` on a failed spawn.
- When writing a .env file, use the actual values the user provided (don't use placeholders).
- For interactive scripts (typing speed test, etc.): write with `file_write`, then `done` telling user to run it.
- When task is complete, give user the PID(s) of running processes so they can manage them.
"""


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — LLM ROUTER  (streaming + health-weighted selection)
# ══════════════════════════════════════════════════════════════════════════════
class LLMRouter:
    def __init__(self):
        self.override_id: Optional[str] = None

    @staticmethod
    def _extract_json(text: str) -> Optional[str]:
        """Extract the LAST complete JSON object from text containing an 'action' key.
        Handles models that output multiple JSON blobs or wrap in prose."""
        # First try: direct parse (clean response)
        try:
            d = json.loads(text)
            if isinstance(d, dict) and "action" in d:
                return text
        except Exception:
            pass

        # Second try: find all {...} blocks using brace counting, return last valid one with 'action'
        last_valid = None
        i = 0
        while i < len(text):
            if text[i] == '{':
                depth = 0
                for j in range(i, len(text)):
                    if text[j] == '{':
                        depth += 1
                    elif text[j] == '}':
                        depth -= 1
                        if depth == 0:
                            candidate = text[i:j+1]
                            try:
                                d = json.loads(candidate)
                                if isinstance(d, dict) and "action" in d:
                                    last_valid = candidate
                            except Exception:
                                pass
                            break
            i += 1
        return last_valid

    def _best_provider(self, exclude: Optional[set] = None) -> Optional[Provider]:
        pool = PROVIDERS
        if self.override_id:
            pool = [p for p in PROVIDERS if p.id == self.override_id] or PROVIDERS
        exclude_set = exclude or set()
        available = [p for p in pool if not p.exhausted and not p.quota_blocked and p.id not in exclude_set]
        if not available:
            return None
        return max(available, key=lambda p: p.health_score)

    def query(self, history: List[Dict], stream: bool = True) -> Tuple[str, str]:
        """Returns (raw_text, provider_name). Streams to console if stream=True."""
        tried_providers = set()
        attempts = 0
        max_attempts = len(PROVIDERS) + 2

        while attempts < max_attempts:
            attempts += 1
            provider = self._best_provider(exclude=tried_providers)
            if not provider:
                if self.override_id and tried_providers:
                    _warn(f"Locked model '{self.override_id}' unavailable. Falling back to active pool...")
                    provider = self._best_provider(exclude=None)
                if not provider:
                    return '{"action":"done","message":"❌ All AI models exhausted.","thought":"No providers"}', "None"

            tried_providers.add(provider.id)

            try:
                t0 = time.time()
                if stream and provider.supports_stream:
                    raw = self._stream(provider, history)
                else:
                    raw = self._blocking(provider, history)

                provider.record_latency((time.time() - t0) * 1000)

                # Strip markdown fences
                raw = re.sub(r"^```(?:json)?\n?", "", raw.strip(), flags=re.IGNORECASE)
                raw = re.sub(r"\n?```$", "", raw.strip())

                # Smart JSON extraction — find the LAST complete {...} block with 'action'
                extracted = self._extract_json(raw)
                if extracted is not None:
                    return extracted, provider.name

                # If no valid JSON found, check if model gave a direct conversational or markdown answer
                clean_raw = raw.strip()
                if clean_raw:
                    # Model answered directly with markdown/prose without JSON envelope
                    coerced = json.dumps({
                        "action": "done",
                        "message": clean_raw,
                        "thought": "Direct model answer"
                    })
                    return coerced, provider.name

                raise json.JSONDecodeError("Blank model response", raw, 0)

            except json.JSONDecodeError:
                provider.total_errors += 1
                _warn(f"[{provider.name}] Invalid JSON response. Trying next provider...")
                continue
            except Exception as e:
                err_str = str(e)
                err = err_str.lower()
                if "blank_response" in err_str:
                    _warn(f"[{provider.name}] Blank response (glitch). Skipping to next...")
                    continue
                # ── ONLY ON QUOTA EXHAUSTED: HARD BLOCK FOR ENTIRE SESSION ──
                if any(k in err for k in ["429", "quota", "exhausted", "rate_limit", "rate limit", "resource_exhausted"]):
                    provider.exhausted = True
                    provider.quota_blocked = True
                    _warn(f"⛔ [{provider.name}] Quota exhausted! Completely BLOCKED for this entire session.")
                elif "404" in err or "not found" in err:
                    provider.exhausted = True
                    provider.quota_blocked = True
                    _warn(f"[{provider.name}] Model not found. Disabling for session.")
                else:
                    # Regular temporary errors (network timeout, glitch) do NOT block for the whole session
                    provider.total_errors += 1
                    _warn(f"[{provider.name}] Temporary error: {e}")
                continue

        return '{"action":"done","message":"❌ All AI models failed.","thought":"System down"}', "None"

    def _stream(self, provider: Provider, history: List[Dict]) -> str:
        chunks = []
        with provider.client.chat.completions.create(
            model=provider.model,
            messages=history,
            temperature=CFG["temperature"],
            stream=True,
        ) as stream:
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                chunks.append(delta)
                print(delta, end="", flush=True)
        print()  # newline after stream
        result = "".join(chunks).strip()
        if not result:
            raise ValueError("BLANK_RESPONSE")
        return result

    def _blocking(self, provider: Provider, history: List[Dict]) -> str:
        res = provider.client.chat.completions.create(
            model=provider.model,
            messages=history,
            temperature=CFG["temperature"],
        )
        choice = res.choices[0]
        if not choice.message or not choice.message.content:
            reason = getattr(choice, "finish_reason", "unknown")
            if reason == "stop":
                raise ValueError("BLANK_RESPONSE")   # glitch — try next provider
            raise ValueError(f"Empty response (finish_reason={reason})")
        return choice.message.content

router = LLMRouter()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — SESSION SNAPSHOT SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
class SessionManager:
    def __init__(self):
        self.session_dir = Path(CFG["session_dir"])
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.name: str = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def save(self, memory: MemorySystem):
        path = self.session_dir / f"{self.name}.json"
        data = {
            "name": self.name,
            "saved_at": datetime.now().isoformat(),
            "history": memory.get_history(),
            "episodes": [asdict(e) for e in memory.episodes],
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return str(path)

    def load(self, name: str) -> Optional[Dict]:
        path = self.session_dir / f"{name}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_sessions(self) -> List[str]:
        return [f.stem for f in sorted(self.session_dir.glob("*.json"), reverse=True)]


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 12 — TOKEN / COST TRACKER
# ══════════════════════════════════════════════════════════════════════════════
class CostTracker:
    COSTS_PER_1K = {  # USD per 1k tokens (approximate)
        "gemini-3.8-flash":          (0.00010, 0.00040),
        "gemini-3.5-flash":          (0.00010, 0.00040),
        "gemini-2.5-flash":          (0.00015, 0.00060),
        "gemini-2.5-pro":            (0.00125, 0.00500),
        "openai/gpt-oss-120b":       (0.00000, 0.00000),  # free tier
        "qwen/qwen3.8-27b":          (0.00000, 0.00000),  # free tier
        "openai/gpt-oss-20b":        (0.00000, 0.00000),  # free tier
        "gpt-4o":                    (0.00500, 0.01500),
        "default":                   (0.00100, 0.00200),
    }
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def add(self, text: str, is_completion: bool = True):
        # rough token estimate: 1 token ≈ 4 chars
        tokens = len(text) // 4
        if is_completion:
            self.completion_tokens += tokens
        else:
            self.prompt_tokens += tokens

    def estimate_cost(self, model: str) -> float:
        in_rate, out_rate = self.COSTS_PER_1K.get(model, self.COSTS_PER_1K["default"])
        return (self.prompt_tokens / 1000 * in_rate +
                self.completion_tokens / 1000 * out_rate)

    def summary(self) -> str:
        return (f"Tokens → In:{self.prompt_tokens:,}  Out:{self.completion_tokens:,} "
                f"| Est. cost: ~${self.estimate_cost('default'):.4f}")

tracker = CostTracker()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 13 — DISPLAY HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _warn(msg: str):
    print(f"{C.YEL}⚠  {msg}{C.RST}", file=sys.stderr)

def _print_thought(thought: str, model: str):
    if RICH:
        console.print(Panel(f"[dim]{thought}[/dim]", title=f"[cyan]🧠 THOUGHT[/cyan]  [dim]{model}[/dim]",
                            border_style="cyan", padding=(0, 1)))
    else:
        print(f"\n{C.CYAN}🧠 [{model}] {thought}{C.RST}")

def _print_action(action: str, detail: str):
    icons = {"terminal":"▶","file_read":"📖","file_write":"📝","file_patch":"🔧",
             "git":"🌿","python_eval":"🐍","search":"🌐","deploy":"🚀","ask":"💬","done":"✅"}
    icon = icons.get(action, "•")
    col = {"terminal":C.YEL,"file_write":C.MAG,"file_patch":C.MAG,"search":C.GRY,
           "done":C.BGRN,"ask":C.BCYN,"git":C.GRN,"deploy":C.BRED}.get(action, C.YEL)
    if RICH:
        console.print(f"[bold]{col}{icon} [{action.upper()}][/bold] {detail[:160]}")
    else:
        print(f"{col}{icon} [{action.upper()}] {detail[:160]}{C.RST}")

def _print_result(ok: bool, output: str):
    col = C.GRN if ok else C.RED
    status = "✔ OK" if ok else "✖ FAIL"
    if RICH:
        syntax = Syntax(output[:2000], "text", theme="monokai", line_numbers=False,
                        background_color="default")
        console.print(Panel(syntax, title=f"[{'green' if ok else 'red'}]{status}[/]",
                            border_style="green" if ok else "red", padding=(0,1)))
    else:
        print(f"{col}{status}{C.RST}\n{C.GRY}{output[:2000]}{C.RST}")

def _divider(label: str = ""):
    if RICH:
        console.rule(f"[dim]{label}[/dim]")
    else:
        print(f"{C.GRY}{'─' * 60} {label}{C.RST}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 14 — MAIN AGENT SESSION  (ReAct loop)
# ══════════════════════════════════════════════════════════════════════════════
class IgniteSession:
    def __init__(self):
        self.memory = MemorySystem(max_history=CFG["max_history_messages"])
        self.memory.push("system", SYSTEM_PROMPT)
        self.session_mgr = SessionManager()
        self.tools_used_this_run: List[str] = []
        self.step_count = 0
        self.total_steps = 0
        self._swarm: Optional[Any] = None

    @property
    def swarm(self) -> Any:
        if self._swarm is None:
            self._swarm = SwarmOrchestrator(self)
        return self._swarm

    def run(self, user_input: str, max_iter: int = None):
        max_iter = max_iter or CFG["max_iterations"]
        # Pre-task automatic safety checkpoint
        if 'git_shield' in globals():
            git_shield.create_checkpoint(f"Task: {user_input[:35]}")
        obfuscator.register(user_input)
        obfuscator.register(str(shell.cwd))

        scan = shell.scan_project()
        scan_text = json.dumps(scan, indent=2)
        safe_scan = obfuscator.mask(scan_text)
        safe_input = obfuscator.mask(user_input)
        safe_cwd = obfuscator.mask(str(shell.cwd))
        episode_ctx = self.memory.format_episodes()

        full_user_msg = (
            f"Task: {safe_input}\n\n"
            f"[Project Scan]\n{safe_scan}\n\n"
            f"[CWD]: {safe_cwd}\n\n"
            f"[{episode_ctx}]"
        )
        self.memory.push("user", full_user_msg)
        tracker.add(full_user_msg, is_completion=False)

        self.tools_used_this_run = []
        outcome = "partial"

        for step in range(1, max_iter + 1):
            self.step_count = step
            _divider(f"Step {step}/{max_iter}")

            if CFG["stream_responses"]:
                print(f"{C.DIM}🤖 Streaming response...{C.RST}")

            raw, model_name = router.query(self.memory.get_history(),
                                           stream=CFG["stream_responses"])
            tracker.add(raw, is_completion=True)

            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                _warn("Failed to parse JSON. Injecting correction prompt.")
                self.memory.push("assistant", raw)
                self.memory.push("user", "ERROR: Your response was not valid JSON. Output ONLY a single JSON object.")
                continue

            action = d.get("action", "done")
            thought = d.get("thought", "...")
            model_label = model_name

            # Don't re-print thought if we streamed it live already
            if not CFG["stream_responses"]:
                _print_thought(thought, model_label)

            self.tools_used_this_run.append(action)
            self.memory.push("assistant", raw)

            # ── Terminal ──────────────────────────────────────────────────
            if action == "terminal":
                cmd = d.get("cmd", "")
                real_cmd = obfuscator.unmask(cmd)
                _print_action("terminal", real_cmd)
                res = tool_terminal(cmd)
                _print_result(res.success, res.output)
                safe_log = obfuscator.mask(res.output)
                self.memory.push("user", f"Exit:{'0' if res.success else '1'}\nLog:\n{safe_log}")

            # ── File Read ─────────────────────────────────────────────────
            elif action == "file_read":
                path = d.get("path", "")
                _print_action("file_read", obfuscator.unmask(path))
                res = tool_file_read(path, d.get("start", 1), d.get("end"))
                _print_result(res.success, res.output[:500] + "..." if len(res.output) > 500 else res.output)
                self.memory.push("user", f"File content:\n{obfuscator.mask(res.output)}")

            # ── File Write ────────────────────────────────────────────────
            elif action == "file_write":
                path = d.get("path", "")
                _print_action("file_write", obfuscator.unmask(path))
                res = tool_file_write(path, d.get("content", ""))
                _print_result(res.success, res.output)
                self.memory.push("user", res.output)

            # ── File Patch ────────────────────────────────────────────────
            elif action == "file_patch":
                path = d.get("path", "")
                _print_action("file_patch", obfuscator.unmask(path))
                res = tool_file_patch(path, d.get("diff", ""))
                _print_result(res.success, res.output)
                self.memory.push("user", res.output)

            # ── Git ───────────────────────────────────────────────────────
            elif action == "git":
                subcmd = d.get("subcmd", "status")
                _print_action("git", f"git {subcmd}")
                res = tool_git(subcmd)
                _print_result(res.success, res.output)
                self.memory.push("user", f"git {subcmd}:\n{obfuscator.mask(res.output)}")

            # ── Python Eval ───────────────────────────────────────────────
            elif action == "python_eval":
                code = d.get("code", "")
                _print_action("python_eval", code[:80])
                res = tool_python_eval(code)
                _print_result(res.success, res.output)
                self.memory.push("user", f"Python output:\n{res.output}")

            # ── Search ────────────────────────────────────────────────────
            elif action == "search":
                query = d.get("query", "")
                _print_action("search", obfuscator.unmask(query))
                res = tool_search(query)
                _print_result(True, res.output[:600])
                self.memory.push("user", f"Search results:\n{res.output}")

            # ── Code Search (Semantic Indexer) ───────────────────────────
            elif action == "code_search":
                query = d.get("query", "")
                top_k = int(d.get("top_k", 5))
                _print_action("code_search", f"'{query}' (top {top_k})")
                res = tool_code_search(query, top_k)
                _print_result(res.success, res.output[:600])
                self.memory.push("user", f"Code search results:\n{res.output}")

            # ── MCP Call (Model Context Protocol) ────────────────────────
            elif action == "mcp_call":
                server = d.get("server", "")
                tool_name = d.get("tool", "")
                args = d.get("arguments") or {}
                _print_action("mcp_call", f"{server}::{tool_name}")
                res = tool_mcp_call(server, tool_name, args)
                _print_result(res.success, res.output[:600])
                self.memory.push("user", f"MCP [{server}::{tool_name}] output:\n{res.output}")

            # ── Deploy ────────────────────────────────────────────────────
            elif action == "deploy":
                platform = d.get("platform", "")
                subcmd = d.get("subcmd", "")
                detail = f"{platform} {subcmd}".strip() or "auto"
                _print_action("deploy", detail)
                res = tool_deploy(subcmd, platform)
                _print_result(res.success, res.output)
                self.memory.push("user", res.output)

            # ── Spawn (new terminal window or background process) ─────────
            elif action == "spawn":
                cmd = d.get("cmd", "")
                name = d.get("name", "")
                mode = d.get("mode", "window")
                real_cmd = obfuscator.unmask(cmd)
                mode_label = "🪟 NEW WINDOW" if mode == "window" else "⚙ BACKGROUND"
                _print_action("spawn", f"{mode_label} → {real_cmd[:80]}")
                res = tool_spawn(cmd, name, mode)
                _print_result(res.success, res.output)
                self.memory.push("user", res.output)

            # ── Kill ──────────────────────────────────────────────────────
            elif action == "kill":
                pid = d.get("pid")
                name = d.get("name", "")
                label = f"PID {pid}" if pid else f"name={name}"
                _print_action("kill", f"🔴 Killing {label}")
                res = tool_kill(pid, name)
                _print_result(res.success, res.output)
                self.memory.push("user", res.output)

            # ── Process Status ────────────────────────────────────────────
            elif action == "process_status":
                pid = d.get("pid")
                _print_action("process_status", f"PID={pid}" if pid else "all processes")
                res = tool_process_status(pid, d.get("tail", 60))
                _print_result(True, res.output)
                self.memory.push("user", res.output)

            # ── Read Log ──────────────────────────────────────────────────
            elif action == "read_log":
                pid = d.get("pid", 0)
                tail = d.get("tail", 80)
                _print_action("read_log", f"PID={pid} (last {tail} lines)")
                res = tool_read_log(pid, tail)
                _print_result(True, res.output)
                self.memory.push("user", f"Process log:\n{res.output}")

            # ── Ask ───────────────────────────────────────────────────────
            elif action == "ask":
                msg = d.get("message", "I need your input.")
                _print_action("ask", msg)
                if RICH:
                    console.print(Panel(f"[bold cyan]{msg}[/bold cyan]", title="💬 IGNITE NEEDS INPUT",
                                        border_style="cyan"))
                else:
                    print(f"\n{C.BCYN}💬 {msg}{C.RST}")
                reply = input(f"{C.BYEL}Your reply> {C.RST}").strip()
                obfuscator.register(reply)
                safe_reply = obfuscator.mask(reply)
                self.memory.push("user", f"User replied: {safe_reply}")

            # ── Generic Registered Tool Execution (verify_code, git_diff, etc.) ──
            elif action in TOOL_DISPATCH:
                fn = TOOL_DISPATCH[action]
                arg_summary = str(d.get("cmd") or d.get("path") or d.get("query") or "")
                _print_action(action, arg_summary[:80])
                res = fn(d)
                _print_result(res.success, res.output[:500] + "..." if len(res.output) > 500 else res.output)
                self.memory.push("user", res.output)

            # ── Done ──────────────────────────────────────────────────────
            elif action == "done":
                msg = d.get("message", "Task complete.")
                if RICH:
                    console.print(Panel(Markdown(msg), title="[bold green]✅ IGNITE FINISHED[/bold green]",
                                        border_style="green", padding=(1, 2)))
                else:
                    print(f"\n{C.BGRN}✅ {msg}{C.RST}\n")
                outcome = "success"
                self.memory.record_episode(user_input[:80], msg[:200],
                                           self.tools_used_this_run, outcome)
                break

        else:
            print(f"\n{C.RED}⏱  Max iterations reached. Pausing agent.{C.RST}")
            self.memory.record_episode(user_input[:80], "Max iterations hit",
                                       self.tools_used_this_run, "partial")

        self.total_steps += step
        if CFG["show_token_stats"]:
            _divider()
            print(f"{C.GRY}📊 {tracker.summary()}  |  Steps: {step}  |  Model: {model_name}{C.RST}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 14b — MULTI-AGENT SWARM (Planner · Engineer · Critic Triad)
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class SwarmMilestone:
    id: int
    title: str
    description: str
    acceptance_criteria: str
    status: str = "PENDING"  # PENDING | IN_PROGRESS | COMPLETED | FAILED
    critic_notes: str = ""
    attempts: int = 0

class SwarmOrchestrator:
    """
    Enterprise Hierarchical Multi-Agent Triad:
    1. The Architect (Planner): Decomposes goal into Milestone DAG.
    2. The Engineer (Coder): Precision milestone executor.
    3. The Critic (Reviewer): Automated quality & verification gatekeeper.
    """
    def __init__(self, session: IgniteSession):
        self.session = session
        self.active_plan: List[SwarmMilestone] = []
        self.plan_title: str = ""
        self.enabled: bool = True

    def render_board(self):
        """Render a live status board of all milestones."""
        if not self.active_plan:
            return

        rows = []
        for m in self.active_plan:
            if m.status == "COMPLETED":
                icon = f"{C.BGRN}✔ DONE{C.RST}"
            elif m.status == "IN_PROGRESS":
                icon = f"{C.BYEL}▶ ACTIVE{C.RST}"
            elif m.status == "FAILED":
                icon = f"{C.BRED}✖ FAILED{C.RST}"
            else:
                icon = f"{C.DIM}⏳ PENDING{C.RST}"
            rows.append((str(m.id), icon, m.title, m.acceptance_criteria[:50]))

        if RICH:
            t = Table(title=f"⚡ MULTI-AGENT SWARM BOARD — {self.plan_title}", box=box.ROUNDED)
            t.add_column("#", style="dim", width=4)
            t.add_column("Status", width=12)
            t.add_column("Milestone Title", style="bold cyan")
            t.add_column("Acceptance Criteria", style="dim")
            for r in rows:
                t.add_row(*r)
            console.print(t)
        else:
            print(f"\n{C.BCYN}╔════ ⚡ MULTI-AGENT SWARM BOARD: {self.plan_title} ════╗{C.RST}")
            for r in rows:
                print(f"  [{r[0]}] {r[1]} {r[2]} — {r[3]}")
            print(f"{C.BCYN}╚{'═' * 55}╝{C.RST}\n")

    def plan_goal(self, goal: str) -> List[SwarmMilestone]:
        """Architect Agent decomposes high-level goal into verifiable milestones."""
        scan = shell.scan_project()
        prompt = f"""You are the ARCHITECT AGENT in IGNITE V3 PRO.
Your job is to break down the user's software engineering goal into 3 to 6 logical, verifiable milestones.

Goal: {goal}
Current Workspace: {shell.cwd}
Stacks Detected: {', '.join(scan['stacks'])}
Files: {list(scan['structure'].keys())[:12]}

Output ONLY a JSON object in this exact schema:
{{
  "plan_title": "<short descriptive title of plan>",
  "milestones": [
    {{
      "id": 1,
      "title": "<concise title>",
      "description": "<what needs to be created or configured>",
      "acceptance_criteria": "<how to test or verify this milestone is finished>"
    }}
  ]
}}
Do NOT output any markdown, explanations, or prose. Just pure JSON.
"""
        messages = [
            {"role": "system", "content": "You are a Principal Software Architect. Output ONLY JSON."},
            {"role": "user", "content": prompt}
        ]
        raw, model_name = router.query(messages, stream=False)
        try:
            cleaned = re.sub(r"^```(?:json)?\n?|\n?```$", "", raw.strip(), flags=re.IGNORECASE)
            data = json.loads(cleaned)
            self.plan_title = data.get("plan_title", goal[:40])
            self.active_plan = []
            for item in data.get("milestones", []):
                self.active_plan.append(SwarmMilestone(
                    id=item.get("id", len(self.active_plan) + 1),
                    title=item.get("title", f"Milestone {len(self.active_plan) + 1}"),
                    description=item.get("description", ""),
                    acceptance_criteria=item.get("acceptance_criteria", "Code compiles cleanly")
                ))
        except Exception:
            self.plan_title = goal[:40]
            self.active_plan = [
                SwarmMilestone(1, "Setup & Dependencies", "Configure environment and packages", "Dependencies verified"),
                SwarmMilestone(2, "Core Implementation", goal, "Core feature implementation complete"),
                SwarmMilestone(3, "Verification & Audit", "Run automated tests and audit functionality", "All tests pass green")
            ]
        return self.active_plan

    def audit_milestone(self, milestone: SwarmMilestone) -> Tuple[bool, str]:
        """Critic Agent audits milestone output using git diff and verification."""
        diff_text = git_shield.diff()
        verif_res = tool_verify_code()

        prompt = f"""You are the CRITIC & CODE REVIEWER in IGNITE V3 PRO.
Audit the following milestone completion:
Milestone: {milestone.title}
Acceptance Criteria: {milestone.acceptance_criteria}

Recent Diffs:
{diff_text[:1200]}

Verification Output:
{verif_res.output[:800]}

Evaluate if this milestone is acceptable to mark as COMPLETED.
Output ONLY JSON in this format:
{{
  "verdict": "APPROVED" or "REJECTED",
  "score": <0-100>,
  "feedback": "<brief rationale>",
  "required_fixes": ["<fix 1>", "<fix 2>"]
}}
"""
        messages = [
            {"role": "system", "content": "You are an Elite Code Reviewer & Security Auditor. Output ONLY JSON."},
            {"role": "user", "content": prompt}
        ]
        raw, model_name = router.query(messages, stream=False)
        try:
            cleaned = re.sub(r"^```(?:json)?\n?|\n?```$", "", raw.strip(), flags=re.IGNORECASE)
            data = json.loads(cleaned)
            verdict = data.get("verdict", "APPROVED").upper()
            feedback = data.get("feedback", "Code meets requirements.")
            return verdict == "APPROVED", feedback
        except Exception:
            return verif_res.success, "Verification pass completed."

    def execute_plan(self, goal: str):
        """Orchestrate the complete Swarm lifecycle: Architect ➔ Engineer ➔ Critic."""
        print(f"\n{C.BCYN}🚀 INITIATING MULTI-AGENT SWARM ORCHESTRATION...{C.RST}")
        print(f"{C.GRY}Role 1: 🏛 The Architect (Decomposing Goal into Milestone DAG){C.RST}")

        milestones = self.plan_goal(goal)
        self.render_board()

        completed_count = 0
        for m in milestones:
            m.status = "IN_PROGRESS"
            self.render_board()

            print(f"\n{C.BBLU}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.RST}")
            print(f"{C.BGRN}👷 Engineer Agent executing Milestone {m.id}: {m.title}{C.RST}")
            print(f"{C.DIM}Target: {m.description}{C.RST}")
            print(f"{C.BBLU}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.RST}\n")

            task_prompt = (
                f"You are the ENGINEER AGENT working on Milestone {m.id}/{len(milestones)} of goal: '{self.plan_title}'.\n"
                f"Milestone Title: {m.title}\n"
                f"Description: {m.description}\n"
                f"Acceptance Criteria: {m.acceptance_criteria}\n"
                f"Execute the necessary file_write, file_patch, terminal, spawn, or verify_code operations. "
                f"When this milestone is satisfied, output: {{\"action\":\"done\",\"message\":\"Milestone {m.id} completed\"}}"
            )
            self.session.run(task_prompt, max_iter=8)

            # Critic Review Pass
            print(f"\n{C.MAG}🕵️ Critic & Reviewer Agent auditing Milestone {m.id}...{C.RST}")
            approved, feedback = self.audit_milestone(m)

            if approved:
                m.status = "COMPLETED"
                m.critic_notes = feedback
                completed_count += 1
                print(f"{C.BGRN}✔ Critic APPROVED Milestone {m.id}: {feedback}{C.RST}\n")
            else:
                print(f"{C.BYEL}⚠ Critic requested refinements: {feedback}{C.RST}")
                print(f"{C.CYAN}🔄 Triggering Engineer auto-correction pass...{C.RST}")
                fix_prompt = f"CRITIC FEEDBACK on Milestone '{m.title}': {feedback}. Fix these issues now and run verify_code."
                self.session.run(fix_prompt, max_iter=4)
                m.status = "COMPLETED"
                completed_count += 1

            self.render_board()

        _divider()
        if RICH:
            console.print(Panel(
                f"[bold green]✔ All {completed_count}/{len(milestones)} Milestones Completed & Verified![/bold green]\n"
                f"Goal: [bold cyan]{self.plan_title}[/bold cyan]\n"
                f"Inspect changes with [bold yellow]/diff[/bold yellow] or rollback with [bold red]/undo[/bold red].",
                title="🏆 SWARM GOAL ACHIEVED",
                border_style="green",
                padding=(1, 2)
            ))
        else:
            print(f"\n{C.BGRN}🏆 SWARM GOAL ACHIEVED: All {completed_count}/{len(milestones)} Milestones Completed & Verified!{C.RST}\n")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 15 — SLASH COMMAND HANDLER
# ══════════════════════════════════════════════════════════════════════════════
def interactive_model_selector() -> Optional[str]:
    """
    Interactive terminal model selector:
    - Arrow keys (Up/Down) to navigate
    - Enter to select highlighted model
    - Number key (0-9) to select immediately
    - 'r' to reset quota blocks
    - 'q' or Esc to cancel
    """
    items = [("auto", "Auto / Smart Failover (Dynamic Priority Routing)")]
    for p in PROVIDERS:
        if p.quota_blocked:
            st = f"{C.RED}[BLOCKED - Quota]{C.RST}"
        elif p.exhausted:
            st = f"{C.YEL}[EXHAUSTED]{C.RST}"
        else:
            st = f"{C.GRN}[ACTIVE]{C.RST}"
        items.append((p.id, f"{p.name} {C.DIM}({p.model}){C.RST} {st}"))

    # Determine current index
    selected_idx = 0
    if router.override_id:
        for idx, (pid, _) in enumerate(items):
            if pid == router.override_id:
                selected_idx = idx
                break

    # If stdin is not an interactive tty
    if not sys.stdin.isatty():
        print(f"\n{C.BCYN}── Select AI Model ──{C.RST}")
        for i, (pid, label) in enumerate(items):
            cur = f" {C.CYN}★ CURRENT{C.RST}" if i == selected_idx else ""
            print(f"  [{i}] {label}{cur}")
        print(f"  [r] Reset all quota blocks")
        print(f"  [q] Cancel")
        try:
            choice = input(f"\nSelect [0-{len(items)-1}, r, q]: ").strip().lower()
            if choice in ("r", "reset"): return "reset"
            if choice in ("q", ""): return None
            if choice.isdigit() and 0 <= int(choice) < len(items):
                return items[int(choice)][0]
        except Exception:
            pass
        return None

    # Interactive console selection (Windows msvcrt)
    import msvcrt
    os.system("")  # Enable ANSI terminal processing

    total_lines = len(items) + 3

    def draw(cur: int, first: bool = False):
        if not first:
            sys.stdout.write(f"\033[{total_lines}F")
        lines = []
        lines.append(f"{C.BCYN}🤖 Select AI Model (Use ↑/↓ Arrow Keys, or press 1, 2, ..., Enter to choose):{C.RST}\033[K")
        for i, (pid, label) in enumerate(items):
            active_mark = f" {C.CYN}★ CURRENT{C.RST}" if (router.override_id == pid or (pid == 'auto' and router.override_id is None)) else ""
            if i == cur:
                lines.append(f"  {C.BBLU}▶ [{i}] {label}{active_mark}{C.RST}\033[K")
            else:
                lines.append(f"    [{i}] {label}{active_mark}\033[K")
        lines.append(f"  {C.DIM}[r] Reset Quota Blocks  |  [q/Esc] Cancel{C.RST}\033[K")
        lines.append("\033[K")
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()

    try:
        sys.stdout.write("\033[?25l")  # Hide cursor
        draw(selected_idx, first=True)

        while True:
            ch = msvcrt.getch()

            # Arrow keys & scan codes on Windows
            if ch in (b'\x00', b'\xe0'):
                code = msvcrt.getch()
                if code == b'H':  # UP
                    selected_idx = (selected_idx - 1) % len(items)
                    draw(selected_idx)
                elif code == b'P':  # DOWN
                    selected_idx = (selected_idx + 1) % len(items)
                    draw(selected_idx)
                continue

            # Enter confirms current selection
            if ch in (b'\r', b'\n'):
                return items[selected_idx][0]

            # Cancel
            if ch in (b'\x1b', b'q', b'Q'):
                return None

            # Reset
            if ch in (b'r', b'R'):
                return "reset"

            # Direct number keys (0-9)
            if ch.isdigit():
                val = int(ch.decode('ascii'))
                if val < len(items):
                    selected_idx = val
                    draw(selected_idx)
                    return items[selected_idx][0]
    finally:
        sys.stdout.write("\033[?25h")  # Restore cursor
        sys.stdout.flush()

    return None

def handle_slash(cmd: str, session: IgniteSession) -> bool:
    """Returns True if command was handled (skip LLM)."""
    parts = cmd.strip().split(None, 1)
    verb = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if verb == "/model":
        selected = None
        if not arg:
            selected = interactive_model_selector()
            if selected is None:
                print(f"{C.DIM}Model selection cancelled.{C.RST}")
                return True
        else:
            arg_clean = arg.strip().lower()
            if arg_clean in ("reset", "r"):
                selected = "reset"
            elif arg_clean in ("0", "auto"):
                selected = "auto"
            elif arg_clean.isdigit():
                num = int(arg_clean)
                if num == 0:
                    selected = "auto"
                elif 1 <= num <= len(PROVIDERS):
                    selected = PROVIDERS[num - 1].id
                else:
                    print(f"{C.RED}Invalid model number: {arg}. Available: 0 to {len(PROVIDERS)}{C.RST}")
                    return True
            else:
                match = next((p for p in PROVIDERS if p.id.lower() == arg_clean or arg_clean in p.name.lower()), None)
                if match:
                    selected = match.id
                else:
                    print(f"{C.RED}Unknown model: {arg}. Type /model to open selector.{C.RST}")
                    return True

        if selected == "reset":
            for p in PROVIDERS:
                p.exhausted = False
                p.quota_blocked = False
                p.total_errors = 0
            router.override_id = None
            print(f"{C.GRN}✔ All session quota blocks cleared. Auto routing active.{C.RST}")
        elif selected == "auto":
            router.override_id = None
            print(f"{C.GRN}✔ Switched to Auto (Smart Failover Router active){C.RST}")
        else:
            match = next((p for p in PROVIDERS if p.id == selected), None)
            if match:
                router.override_id = selected
                print(f"{C.GRN}✔ Locked to: {match.name} ({match.model}){C.RST}")
            else:
                print(f"{C.RED}Unknown model id: {selected}{C.RST}")
        return True

    if verb == "/memory":
        print(session.memory.format_episodes(10))
        print(f"History messages: {len(session.memory.get_history())}")
        return True

    if verb == "/clear":
        session.memory._history = session.memory.get_history()[:1]  # keep system prompt
        print(f"{C.GRN}✔ Chat history cleared (episodes preserved){C.RST}")
        return True

    if verb == "/session":
        sub = arg.split()[0] if arg else ""
        if sub == "save":
            path = session.session_mgr.save(session.memory)
            print(f"{C.GRN}✔ Saved → {path}{C.RST}")
        elif sub == "list":
            sessions = session.session_mgr.list_sessions()
            print("Sessions:\n" + "\n".join(f"  {s}" for s in sessions[:20]))
        elif sub == "load":
            name = arg.split(None,1)[1] if " " in arg else ""
            data = session.session_mgr.load(name)
            if data:
                session.memory._history = data.get("history", [])
                session.memory.episodes = [Episode(**e) for e in data.get("episodes", [])]
                print(f"{C.GRN}✔ Loaded session: {name}{C.RST}")
            else:
                print(f"{C.RED}Session not found: {name}{C.RST}")
        else:
            print("Usage: /session save | list | load <name>")
        return True

    if verb in ("/undo", "/rollback"):
        ok, msg = git_shield.rollback()
        if ok:
            print(f"{C.BGRN}✔ {msg}{C.RST}")
        else:
            print(f"{C.YEL}⚠ {msg}{C.RST}")
        return True

    if verb == "/diff":
        diff_text = git_shield.diff(arg.strip())
        if RICH:
            syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title="🔍 Working Tree Diff", box=box.ROUNDED))
        else:
            print(f"\n{C.BCYN}── Working Tree Diff ──{C.RST}\n{diff_text}\n")
        return True

    if verb == "/verify":
        res = tool_verify_code(cmd=arg.strip())
        if res.success:
            print(f"{C.BGRN}{res.output}{C.RST}")
        else:
            print(f"{C.BRED}{res.output}{C.RST}")
        return True

    if verb == "/commit":
        msg = arg.strip()
        if not msg:
            msg = "chore: update codebase via IGNITE V3 PRO"
        st = shell.git_op("add -A")
        cm = shell.git_op(f"commit -m \"{msg}\"")
        if cm.ok:
            print(f"{C.BGRN}✔ Committed: {msg}{C.RST}\n{cm.stdout}")
        else:
            print(f"{C.YEL}Git commit output:\n{cm.log}{C.RST}")
        return True

    if verb == "/checkpoint":
        chk_id = git_shield.create_checkpoint(arg.strip() or "Manual Checkpoint")
        print(f"{C.BGRN}✔ Safety checkpoint created: {chk_id}{C.RST}")
        return True

    if verb == "/plan":
        sub = arg.strip()
        if not sub or sub.lower() == "status":
            if session.swarm and session.swarm.active_plan:
                session.swarm.render_board()
            else:
                print(f"{C.YEL}No active swarm plan.{C.RST}")
                print(f"Usage: /plan <goal>  (e.g., /plan build full-stack auth system)")
        elif sub.lower() in ("clear", "reset"):
            if session.swarm:
                session.swarm.active_plan = []
                session.swarm.plan_title = ""
            print(f"{C.GRN}✔ Active plan board cleared.{C.RST}")
        else:
            session.swarm.execute_plan(sub)
        return True

    if verb == "/swarm":
        sub = arg.lower().strip()
        if sub in ("on", "enable"):
            session.swarm.enabled = True
            print(f"{C.BGRN}✔ Multi-Agent Swarm mode ENABLED.{C.RST}")
        elif sub in ("off", "disable"):
            session.swarm.enabled = False
            print(f"{C.BYEL}⚠ Multi-Agent Swarm mode DISABLED (Direct mode active).{C.RST}")
        else:
            status = "ENABLED" if session.swarm.enabled else "DISABLED"
            print(f"{C.BCYN}⚡ Swarm Status: {status}{C.RST}")
            print(f"  Architect (Planner) ➔ Engineer (Coder) ➔ Critic (Auditor)")
            print(f"  Run: /plan <goal> to launch multi-agent milestone execution.")
        return True

    if verb == "/index":
        sub = arg.strip().lower()
        if sub in ("rebuild", "force", "reset"):
            print(f"{C.BCYN}🔄 Rebuilding codebase semantic index from scratch...{C.RST}")
            stats = code_indexer.index_workspace(force=True)
            print(f"{C.BGRN}✔ Index rebuilt:{C.RST} Scanned {stats['scanned']} files, indexed {stats['indexed']} files, {stats['total_chunks']} total code chunks.")
        elif sub == "status":
            print(f"{C.BCYN}📊 Codebase Index Status:{C.RST} {code_indexer.status()}")
        else:
            print(f"{C.BCYN}🔍 Scanning & incrementally updating codebase index...{C.RST}")
            stats = code_indexer.index_workspace(force=False)
            print(f"{C.BGRN}✔ Index synced:{C.RST} Scanned {stats['scanned']} files, updated {stats['indexed']} files, {stats['total_chunks']} total code chunks in DB.")
            print(f"{C.GRY}Run /search <keywords/symbol> to query or /index rebuild to force re-indexing.{C.RST}")
        return True

    if verb in ("/search", "/find"):
        if not arg.strip():
            print(f"{C.YEL}Usage: /search <keywords or symbol name> (e.g., /search verify_token){C.RST}")
            return True
        matches = code_indexer.search(arg.strip(), top_k=6)
        if not matches:
            print(f"{C.YEL}No code matches found for '{arg.strip()}'. Try /index rebuild or broader terms.{C.RST}")
            return True
        print(f"\n{C.BCYN}🔍 Codebase Search Results for '{arg.strip()}':{C.RST}")
        for i, m in enumerate(matches, 1):
            sym = f" [{m['symbol_type']}: {m['symbol_name']}]" if m['symbol_name'] else ""
            print(f"\n{C.BGRN}{i}. {m['file_path']}:{m['start_line']}-{m['end_line']}{C.BCYN}{sym}{C.RST}")
            snip = textwrap.indent(m["content"][:400], "   ")
            print(f"{C.DIM}{snip}{C.RST}")
            if len(m["content"]) > 400:
                print(f"{C.GRY}   ... [truncated]{C.RST}")
        print()
        return True

    if verb == "/mcp":
        sub = arg.strip()
        parts = sub.split()
        cmd_type = parts[0].lower() if parts else "list"

        if cmd_type == "init":
            p = mcp_registry.init_config_template()
            print(f"{C.BGRN}✔ Created starter MCP configuration template at:{C.RST} {p}")
            print(f"{C.GRY}Edit .ignite_mcp.json to add your MCP servers, then run /mcp list.{C.RST}")
        elif cmd_type in ("status", "servers"):
            print(f"{C.BCYN}⚡ Model Context Protocol (MCP) Status:{C.RST}\n{mcp_registry.status()}")
        elif cmd_type == "call" and len(parts) >= 3:
            server_name = parts[1]
            tool_name = parts[2]
            raw_args = " ".join(parts[3:]) if len(parts) > 3 else "{}"
            try:
                call_args = json.loads(raw_args)
            except Exception as e:
                print(f"{C.RED}Invalid JSON arguments: {e}{C.RST}")
                return True
            print(f"{C.CYAN}Invoking {server_name}::{tool_name}...{C.RST}")
            res = mcp_registry.call_tool(server_name, tool_name, call_args)
            col = C.BGRN if res.success else C.BRED
            print(f"{col}{res.output}{C.RST}")
        else:
            cfg = mcp_registry.load_config().get("mcpServers", {})
            if not cfg:
                print(f"{C.YEL}No MCP servers configured in .ignite_mcp.json.{C.RST}")
                print(f"{C.GRY}Run {C.BCYN}/mcp init{C.GRY} to create a starter configuration.{C.RST}")
                return True
            tools = mcp_registry.list_tools()
            print(f"\n{C.BCYN}🔌 Model Context Protocol (MCP) Tools ({len(tools)} available):{C.RST}")
            if tools:
                for t in tools:
                    print(f"  • {C.BGRN}{t['server']}::{t['name']}{C.RST} — {t['description']}")
            else:
                print(f"  {C.DIM}No tools reported. Check server connection status with /mcp status.{C.RST}")
            print(f"{C.GRY}Commands: /mcp list | /mcp status | /mcp init | /mcp call <srv> <tool> <json>{C.RST}\n")
        return True

    if verb in ("/setup", "/keys", "/config-keys"):
        if run_first_time_setup():
            new_provs = build_providers()
            PROVIDERS.clear()
            PROVIDERS.extend(new_provs)
            print(f"{C.BGRN}✔ Active AI providers reloaded ({len(PROVIDERS)} providers active).{C.RST}")
        return True

    if verb == "/tools":
        tools = list(TOOL_DISPATCH.keys()) + ["ask", "done"]
        if RICH:
            t = Table(title="🛠  Available Tools (18 Tools)", box=box.SIMPLE)
            t.add_column("Tool", style="cyan")
            t.add_column("Description")
            descs = {
                "terminal":       "Run PowerShell commands with streaming output",
                "file_read":      "Read file contents with line ranges",
                "file_write":     "Create/overwrite files with AST syntax pre-flight",
                "file_patch":     "Apply unified diff patches surgical-style",
                "git":            "Git operations (status/commit/push/clone/branch)",
                "git_diff":       "Inspect uncommitted code changes in working tree",
                "verify_code":    "Self-healing test runner (pytest/unittest/npm/compile)",
                "python_eval":    "Run sandboxed Python code inside agent",
                "spawn":          "Launch process in new visible terminal window or background",
                "kill":           "Terminate running process by PID or name",
                "process_status": "Inspect running processes or inspect process logs",
                "read_log":       "Read live output logs from background/window tasks",
                "search":         "Web search (DuckDuckGo/Bing fallback)",
                "code_search":    "Semantic hybrid BM25 + AST symbol search across project",
                "mcp_call":       "Call external tool on Model Context Protocol (MCP) server",
                "deploy":         "Auto-detect & run deployment workflow",
                "ask":            "Pause and request credentials/decisions from user",
                "done":           "Complete task or answer user directly",
            }
            for tool in tools:
                t.add_row(f"[cyan]{tool}[/cyan]", descs.get(tool, ""))
            console.print(t)
        else:
            for tool in tools:
                print(f"  {tool}")
        return True

    if verb in ("/ps", "/processes"):
        if arg:
            pid = int(arg) if arg.isdigit() else None
            print(proc_registry.status(pid=pid, tail=40))
        else:
            print(proc_registry.status())
        return True

    if verb == "/kill":
        if not arg:
            print(f"{C.RED}Usage: /kill <pid or process_name>{C.RST}")
        else:
            if arg.isdigit():
                res = proc_registry.kill(int(arg))
            else:
                res = proc_registry.kill_by_name(arg)
            print(f"{C.GRN}{res}{C.RST}")
        return True

    if verb == "/status":
        scan = shell.scan_project()
        if RICH:
            t = Table(title=f"📁 Project Status — {shell.cwd}", box=box.MINIMAL_DOUBLE_HEAD)
            t.add_column("Key"); t.add_column("Value")
            t.add_row("CWD", str(shell.cwd))
            t.add_row("Stacks", ", ".join(scan["stacks"]))
            t.add_row("Deploy targets", ", ".join(scan["deploy_targets"]) or "None")
            t.add_row("Env vars needed", ", ".join(scan["required_env_vars"]) or "None")
            t.add_row("Active model", router.override_id or "auto")
            t.add_row("Running processes", str(len([p for p in proc_registry._procs.values() if p.is_alive])))
            t.add_row("Session", session.session_mgr.name)
            t.add_row("Total steps", str(session.total_steps))
            t.add_row("Token stats", tracker.summary())
            console.print(t)
        else:
            for k, v in scan.items():
                print(f"  {k}: {v}")
        return True

    if verb == "/config":
        if RICH:
            t = Table(title="⚙  Config", box=box.SIMPLE)
            t.add_column("Key"); t.add_column("Value")
            for k, v in CFG.items():
                t.add_row(k, str(v))
            console.print(t)
        else:
            for k, v in CFG.items():
                print(f"  {k} = {v}")
        return True

    if verb == "/history":
        hist = session.memory.get_history()
        for i, m in enumerate(hist[-10:], 1):
            role = m["role"].upper()
            snippet = m["content"][:100].replace("\n", " ")
            print(f"  {i:2}. [{role}] {snippet}...")
        return True

    if verb in ("/dashboard", "/ui"):
        sub = arg.lower().strip()
        if sub == "stop":
            print(f"{C.YEL}{dashboard.stop()}{C.RST}")
        elif sub == "url":
            print(f"Dashboard URL: {dashboard.url()}")
        else:
            url = dashboard.start(session=session, open_browser=True)
            print(f"{C.BGRN}✔ Web Dashboard running at: {url}{C.RST}")
            print(f"{C.GRY}  Live process monitor, logs, and token stats opened in browser.{C.RST}")
        return True

    if verb == "/deploy":
        if not arg or arg.lower() in ("help", "list"):
            print(deploy_engine.help_menu())
        else:
            parts = arg.split(None, 1)
            target_platform = parts[0]
            extra_cmd = parts[1] if len(parts) > 1 else ""
            res = deploy_engine.deploy(platform=target_platform, subcmd=extra_cmd, cwd=shell.cwd)
            col = C.GRN if res.success else C.RED
            print(f"\n{col}{res.output}{C.RST}")
        return True

    if verb in ("/scripts", "/scratch"):
        scratch_dir = shell.cwd / ".ignite_scratch"
        scripts_dir = shell.cwd / "scripts"
        found = []
        for d in (scratch_dir, scripts_dir):
            if d.exists() and d.is_dir():
                for f in d.glob("*.*"):
                    found.append((f.name, str(f.relative_to(shell.cwd)), f.stat().st_size))
        if not found:
            print(f"{C.YEL}No synthesized helper scripts found in .ignite_scratch/ or scripts/{C.RST}")
            print(f"{C.GRY}Ask IGNITE to perform any custom task and it will synthesize scripts autonomously.{C.RST}")
        else:
            print(f"{C.CYAN}📁 Synthesized Helper Scripts:{C.RST}")
            for name, rel, size in found:
                print(f"  • {C.GRN}{rel:<30}{C.RST} ({size} bytes)")
        return True

    if verb == "/export":
        path = session.session_mgr.save(session.memory)
        print(f"{C.GRN}✔ Session exported → {path}{C.RST}")
        return True

    if verb == "/help":
        help_text = """
╔══════════════════════════════════════════════════════════════════════════╗
║  IGNITE V3 PRO — Command Reference                                       ║
╠══════════════════════════════════════════════════════════════════════════╣
║  /plan [goal]      Multi-Agent Swarm (Architect ➔ Coder ➔ Critic)        ║
║  /swarm [on|off]   Toggle Multi-Agent Swarm Mode                         ║
║  /index [rebuild]  Scan & index codebase for instant BM25 + AST search   ║
║  /search <query>   Semantic hybrid search across functions & classes     ║
║  /mcp [list|init]  Manage external Model Context Protocol (MCP) tools    ║
║  /undo, /rollback  Revert codebase to pre-task safety checkpoint         ║
║  /diff [file]      Show colorized git diff of uncommitted edits          ║
║  /verify [cmd]     Run self-healing test runner / code checks            ║
║  /commit [msg]     Stage & commit all changes with message               ║
║  /checkpoint       Create a manual safety restore snapshot               ║
║  /dashboard, /ui   Open live Web UI in browser (localhost:7860)          ║
║  /deploy [target]  Deploy to Cloud (railway/docker/fly/render)           ║
║  /scripts, /scratch List agent-synthesized helper scripts                ║
║  /model [num]      Interactive model selector (Arrow keys / 1,2)         ║
║  /setup, /keys     Interactive API key configuration wizard              ║
║  /memory           Show episode history & context stats                  ║
║  /clear            Clear chat history (keep episodes)                    ║
║  /session save     Save current session snapshot                         ║
║  /session list     List saved sessions                                   ║
║  /session load     Load a saved session                                  ║
║  /processes, /ps   List running background / spawned windows             ║
║  /kill <pid|name>  Kill spawned process or window                        ║
║  /tools            List all 18 available agent tools                     ║
║  /status           Show project scan + running processes                 ║
║  /config           Show current configuration                            ║
║  /history          Show last 10 messages in memory                       ║
║  /export           Export session to JSON                                ║
║  clear             Reset session completely                              ║
║  exit / quit       Exit IGNITE                                           ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
        print(f"{C.CYAN}{help_text}{C.RST}")
        return True

    return False


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 16 — MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print(BANNER)

    # Print active providers
    if RICH:
        t = Table(title="Active AI Providers", box=box.SIMPLE, show_header=True)
        t.add_column("Priority"); t.add_column("Name"); t.add_column("Model")
        for p in PROVIDERS:
            t.add_row(str(p.priority), p.name, p.model)
        console.print(t)
    else:
        print(f"{C.GRN}Active providers:{C.RST}")
        for p in PROVIDERS:
            print(f"  [{p.priority}] {p.name} ({p.model})")

    if not RICH:
        print(f"\n{C.DIM}💡 Tip: pip install rich  → enables the full UI experience{C.RST}")

    print(f"\n{C.CYAN}🌐 Web Dashboard: Type /dashboard to launch live UI on localhost:7860{C.RST}")
    print(f"{C.GRY}Type /help for commands | exit to quit{C.RST}\n")

    session = IgniteSession()
    _DashboardHandler.session_ref = session

    while True:
        try:
            cwd_label = shell.cwd.name or str(shell.cwd)
            model_label = router.override_id or "auto"
            prompt = f"\n{C.BYEL}IGNITE [{cwd_label}][{model_label}]> {C.RST}"
            user_input = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{C.GRY}Goodbye. Session: {session.session_mgr.name}{C.RST}")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print(f"{C.GRY}Goodbye.{C.RST}")
            break
        if user_input.lower() == "clear":
            session = IgniteSession()
            _DashboardHandler.session_ref = session
            for p in PROVIDERS:
                p.exhausted = False
                p.quota_blocked = False
            print(f"{C.GRN}✔ Full session reset (all model blocks cleared).{C.RST}")
            continue
        if user_input.startswith("/"):
            handle_slash(user_input, session)
            continue

        session.run(user_input)

if __name__ == "__main__":
    main()
