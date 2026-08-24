import os, sys, subprocess, socket, time

# All paths below are derived from the current Windows user profile, so this
# script works unmodified on any machine. Qdrant server itself lives outside
# any user/AppData folder (C:\qdrant-server) so it survives profile changes.
USERPROFILE   = os.environ['USERPROFILE']
QDRANT_EXE    = os.path.join(USERPROFILE, 'uv-bin', 'qdrant.exe')
QDRANT_CONFIG = r'C:\qdrant-server\config.yaml'
QDRANT_CWD    = r'C:\qdrant-server'
QDRANT_HOST   = '127.0.0.1'
QDRANT_PORT   = 6333

def qdrant_running():
    try:
        with socket.create_connection((QDRANT_HOST, QDRANT_PORT), timeout=1):
            return True
    except OSError:
        return False

def start_qdrant():
    CREATE_NO_WINDOW = 0x08000000
    DETACHED_PROCESS = 0x00000008
    subprocess.Popen(
        [QDRANT_EXE, '--config-path', QDRANT_CONFIG],
        cwd=QDRANT_CWD,
        creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(20):
        time.sleep(0.5)
        if qdrant_running():
            return
    raise RuntimeError('Qdrant did not start within 10 seconds')

# Ergaenze Environment fuer uvx/asyncio auf Windows
env = os.environ.copy()
env.setdefault('QDRANT_URL', 'http://127.0.0.1:6333')
env.setdefault('COLLECTION_NAME', 'claude_code_memory')
env.setdefault('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
env.setdefault('UV_CACHE_DIR', os.path.join(USERPROFILE, 'uv-cache'))
env.setdefault('UV_TOOL_DIR', os.path.join(USERPROFILE, 'uv-tools'))

# Kritisch: SystemRoot muss gesetzt sein fuer Windows-DLLs (asyncio/Winsock)
env.setdefault('SystemRoot', r'C:\Windows')
env.setdefault('SYSTEMROOT', r'C:\Windows')
env.setdefault('USERPROFILE', USERPROFILE)
env.setdefault('APPDATA', os.environ.get('APPDATA', os.path.join(USERPROFILE, 'AppData', 'Roaming')))
env.setdefault('LOCALAPPDATA', os.environ.get('LOCALAPPDATA', os.path.join(USERPROFILE, 'AppData', 'Local')))
env.setdefault('TEMP', os.environ.get('TEMP', os.path.join(USERPROFILE, 'AppData', 'Local', 'Temp')))
env.setdefault('TMP', os.environ.get('TMP', os.path.join(USERPROFILE, 'AppData', 'Local', 'Temp')))

if not qdrant_running():
    start_qdrant()

proc = subprocess.Popen(
    [os.path.join(USERPROFILE, 'uv-bin', 'uvx.exe'), 'mcp-server-qdrant'],
    stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr,
    env=env
)
sys.exit(proc.wait())
