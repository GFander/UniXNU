"""Symbol names of the XNU kernel of a build tree, for the archives that must not collide with it."""
import subprocess
from pathlib import Path

_OBJ_ROOT = Path('build/xnu/ios-obj')


def _obj_dir(root=Path('.')):
    """The object directory of this tree's kernel pass, whatever machine config it used."""
    candidates = sorted((Path(root) / _OBJ_ROOT).glob('DEVELOPMENT_ARM64_*'))
    return candidates[0].relative_to(Path(root)) if candidates else _OBJ_ROOT / 'DEVELOPMENT_ARM64_BCM2837'


OBJ = _obj_dir()


def defined_names(paths, global_only):
    """Defined symbol names of Mach-O files and archives."""
    names = set()
    paths = [str(path) for path in paths]
    for start in range(0, len(paths), 200):
        command = ['xcrun', 'nm', *(['-g'] if global_only else []), '-U', '-j', *paths[start:start + 200]]
        names |= {line.strip() for line in subprocess.check_output(command, text=True).splitlines() if line.startswith('_')}
    return names


def kernel_names(root, global_only=True):
    """Names of the XNU kernel alone: the recorded checkpoint kernel if present, else the objects of this tree's XNU link
    (link.filelist, written by every kernel pass before it links). A kernel linked with the archives of this tree would
    contain their own names, so it is not used."""
    root = Path(root)
    checkpoint = root / 'build/xnu/checkpoints/native-4k-user-abi/kernel.macho'
    if checkpoint.is_file():
        return defined_names([checkpoint], global_only)
    filelist = root / OBJ / 'link.filelist'
    if not filelist.is_file():
        # link.filelist is only written by the xnu_libraries pass; the kernel
        # objects of a normal pass carry the same names.
        # genassym.o is a generated header container, not a Mach-O object.
        objects = sorted(o for o in (root / OBJ).rglob('*.o')
                         if o.name != 'genassym.o')
        if not objects:
            raise SystemExit('No XNU symbol names: run a kernel pass first')
        return defined_names(objects, global_only)
    names = defined_names([line.strip() for line in filelist.read_text().splitlines() if line.strip()], global_only)
    # The link also exports aliases (all-alias.exp: "_real _alias") that no object defines under that name.
    aliases = root / OBJ / 'all-alias.exp'
    if aliases.is_file():
        names |= {word for line in aliases.read_text().splitlines() for word in line.split() if word.startswith('_')}
    return names
