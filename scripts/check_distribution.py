"""Build sdist, rebuild its wheel, then smoke-test installation outside the checkout."""
import argparse
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--uv', default='uv')
args = parser.parse_args()
def run(*command, cwd=None):
    subprocess.run(command, cwd=cwd or ROOT, check=True)

with tempfile.TemporaryDirectory(prefix='helloagents-dist-') as temp:
    temp = Path(temp)
    run(args.uv, 'build', '--sdist', '--out-dir', str(temp/'dist'))
    archive = next((temp/'dist').glob('*.tar.gz'))
    unpack = temp/'source'
    unpack.mkdir()
    with tarfile.open(archive) as source:
        # Reject traversal and links even in a locally built source archive.
        for member in source.getmembers():
            target = (unpack/member.name).resolve()
            if not target.is_relative_to(unpack.resolve()) or member.issym() or member.islnk():
                raise ValueError('Unsafe source archive member')
        source.extractall(unpack)
    checkout = next(unpack.iterdir())
    run(args.uv, 'build', '--wheel', '--out-dir', str(temp/'wheel'), cwd=checkout)
    wheel = next((temp/'wheel').glob('*.whl'))
    with zipfile.ZipFile(wheel) as artifact:
        assert artifact.testzip() is None
        assert 'hello_agents/py.typed' in artifact.namelist()
        for path in (ROOT/'hello_agents').rglob('*.py'):
            assert artifact.read(path.relative_to(ROOT).as_posix()) == path.read_bytes(), path
    env = temp/'env'
    run(args.uv, 'venv', str(env), '--python', sys.executable)
    python = env/('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    run(args.uv, 'pip', 'install', '--python', str(python), str(wheel))
    run(args.uv, 'pip', 'check', '--python', str(python))
    run(str(python), '-I', '-c', '''
from pathlib import Path
import hello_agents
from hello_agents import SimpleAgent, RunBudget
from hello_agents.memory import MemoryStore, ProfileStore
from hello_agents.retrieval import RAGStore
from hello_agents.background import JobQueue
from hello_agents.retrieval.evaluation import ranking_metrics
assert Path(hello_agents.__file__).with_name('py.typed').exists()
assert ranking_metrics(['a'], {'a':1})['mrr_at_k'] == 1
print('Installed wheel imports and core interfaces passed:', hello_agents.__file__)
''', cwd=temp)
print('sdist -> wheel -> isolated installation passed')
