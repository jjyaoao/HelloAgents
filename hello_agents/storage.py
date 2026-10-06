"""SQLite 版本校验、事务迁移与一致性备份。

应用画像的 Schema 转换仍由应用代码显式完成。
备份可能包含私有数据，本模块不上传或加密备份。
"""
from contextlib import closing
from pathlib import Path
import sqlite3


class SchemaVersionError(RuntimeError):
    pass


def guard_schema(db, component, version=1):
    """将已知的未标记版本 Schema 认作 v1，拒绝未知的后续版本格式。"""
    db.execute('CREATE TABLE IF NOT EXISTS helloagents_schema(component TEXT PRIMARY KEY, version INTEGER NOT NULL)')
    row = db.execute('SELECT version FROM helloagents_schema WHERE component=?', (component,)).fetchone()
    if row is None:
        db.execute('INSERT OR IGNORE INTO helloagents_schema VALUES(?,?)', (component, version))
        row = db.execute('SELECT version FROM helloagents_schema WHERE component=?', (component,)).fetchone()
    if row[0] != version:
        raise SchemaVersionError(f'{component} schema {row[0]} cannot be opened by schema {version}')
    db.commit()


def backup_database(source, destination):
    """创建包含已提交 WAL 数据的一致性快照，不覆盖已有文件。"""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_file() or source == destination:
        raise ValueError('source must exist; destination must be a different file')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb'):
        pass
    try:
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as src:
            with closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
                if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise RuntimeError('backup integrity check failed')
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination


def migrate_database(path, component, target, migrations):
    """显式备份后，原子执行从当前版本到下一版本的迁移回调。

    回调是受信任的宿主代码，只使用 execute 或 executemany，不调用 commit 或
    executescript。新版库必须声明对应的新版本号，才能打开迁移后的数据。
    """
    if type(target) is not int or target < 1:
        raise ValueError('target must be a positive version')
    if not Path(path).is_file():
        raise FileNotFoundError(path)
    with closing(sqlite3.connect(path)) as db:
        try:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT version FROM helloagents_schema WHERE component=?', (component,)).fetchone()
            if row is None or row[0] > target:
                raise SchemaVersionError('Unknown component or downgrade requested')
            for version in range(row[0], target):
                if version not in migrations:
                    raise SchemaVersionError(f'Missing migration from {version}')
                migrations[version](db)
                if not db.in_transaction:
                    raise SchemaVersionError('Migration callback ended transaction')
                db.execute('UPDATE helloagents_schema SET version=? WHERE component=?', (version+1, component))
            db.commit()
        except BaseException:
            db.rollback()
            raise
