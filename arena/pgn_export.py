"""Bounded PGN downloads from immutable records in a consistent WAL snapshot."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
from aiohttp import web
from .pgn_format import PgnContext, render_attempt, options


class OfficialPgnReader:
    def __init__(self,path,tid,style='compact',perspective='engine',annotations=None):
        self.style,self.perspective,self.annotations=options(style,perspective,annotations)
        self.db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True,timeout=30)
        try:
            self.db.execute('BEGIN')
            self.context=PgnContext(self.db,tid)
            self.cursor=self.db.execute('''SELECT official FROM games
                WHERE tid=? AND invalid=0 AND official IS NOT NULL ORDER BY number''',(tid,))
        except BaseException:
            self.db.close();raise

    def chunk(self):
        return ''.join(render_attempt(self.db,r[0],self.style,self.perspective,self.annotations,self.context)
                       for r in self.cursor.fetchmany(16)).encode('utf-8')

    def close(self):self.db.close()


async def stream_official(request,path,tid):
    # One ordered reader worker per download; network backpressure limits queued
    # data to one chunk. Cancellation queues close after any in-flight read.
    executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='PgnDownload')
    loop=asyncio.get_running_loop();reader=[]
    annotations=request.query.get('annotations')
    annotations=None if annotations is None else [v for v in annotations.split(',') if v]
    def open_reader():reader.append(OfficialPgnReader(path,tid,request.query.get('style','compact'),request.query.get('perspective','engine'),annotations))
    def read():return reader[0].chunk()
    def close():
        if reader:reader[0].close()
    try:
        await loop.run_in_executor(executor,open_reader)
        response=web.StreamResponse(headers={'Content-Type':'application/x-chess-pgn; charset=utf-8',
            'Content-Disposition':f'attachment; filename="official-{tid}.pgn"'})
        await response.prepare(request)
        while chunk:=await loop.run_in_executor(executor,read):await response.write(chunk)
        await response.write_eof()
        return response
    finally:
        try:await asyncio.shield(loop.run_in_executor(executor,close))
        finally:executor.shutdown(wait=False)
