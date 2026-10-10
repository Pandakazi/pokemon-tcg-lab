"""Manual wrapper around the existing paced importer; no scheduler or retries."""
from contextlib import closing
from datetime import datetime,timedelta,timezone
from math import ceil
import sqlite3
from uuid import uuid4


class ManualCompetitiveSync:
    def __init__(self,store,runner=None,clock=None):
        self.store=store
        self.runner=runner
        self.clock=clock or (lambda:datetime.now(timezone.utc))

    def status(self):
        now=self.clock();row=None;last=None
        try:
            with closing(self.store.connect()) as db:
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='competitive_manual_sync'").fetchone():
                    row=db.execute('SELECT * FROM competitive_manual_sync WHERE source=?',('limitless-main',)).fetchone()
                last=db.execute('SELECT max(fetched_at) FROM competitive_events WHERE source=?',('limitless-main',)).fetchone()[0]
        except (OSError,sqlite3.Error):pass
        success=row['success_at'] if row else None
        available=datetime.fromisoformat(success)+timedelta(hours=1) if success else None
        remaining=max(0,ceil((available-now).total_seconds())) if available else 0
        running=bool(row and row['token'] and datetime.fromisoformat(row['started_at'])+timedelta(hours=2)>now)
        return dict(status='running' if running else 'cooldown' if remaining else 'ready',
            last_successful_at=success or (row['baseline_at'] if row else last),manual_success_at=success,
            available_at=available.isoformat() if available else None,retry_after_seconds=remaining,
            failed=bool(row and row['failed']),source='limitless-main')

    def run(self):
        self.store.initialize()
        token=uuid4().hex;now=self.clock()
        with closing(self.store.connect(True)) as db,db:
            db.execute('CREATE TABLE IF NOT EXISTS competitive_manual_sync (source TEXT PRIMARY KEY,success_at TEXT,started_at TEXT,token TEXT,failed INTEGER NOT NULL DEFAULT 0,baseline_at TEXT)')
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM competitive_manual_sync WHERE source=?',('limitless-main',)).fetchone()
            if row and (row['success_at'] and datetime.fromisoformat(row['success_at'])+timedelta(hours=1)>now or
                        row['token'] and datetime.fromisoformat(row['started_at'])+timedelta(hours=2)>now):
                return self.status()
            last=db.execute('SELECT max(fetched_at) FROM competitive_events WHERE source=?',('limitless-main',)).fetchone()[0]
            db.execute('INSERT INTO competitive_manual_sync VALUES (?,?,?,?,0,?) ON CONFLICT(source) DO UPDATE SET started_at=excluded.started_at,token=excluded.token,failed=0',('limitless-main',None,now.isoformat(),token,last))
        try:
            if self.runner is None:
                from .ingest_competitive import refresh
                refresh(self.store,days=90,max_events=25,progress=lambda _:None)
            else:self.runner(self.store)
        except Exception:
            with closing(self.store.connect(True)) as db,db:
                db.execute('UPDATE competitive_manual_sync SET token=NULL,failed=1 WHERE source=? AND token=?',('limitless-main',token))
            return dict(self.status(),status='failed')
        with closing(self.store.connect(True)) as db,db:
            db.execute('UPDATE competitive_manual_sync SET token=NULL,failed=0,success_at=? WHERE source=? AND token=?',(self.clock().isoformat(),'limitless-main',token))
        return dict(self.status(),status='complete')
