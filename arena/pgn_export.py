"""Bounded PGN downloads from immutable records in a consistent WAL snapshot."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
from aiohttp import web
from .pgn_format import PgnContext, render_attempt, options
from .pgn_options import normalize,from_query


class OfficialPgnReader:
    def __init__(self,path,tid,style='compact',perspective='engine',annotations=None,*,export_options=None):
        self.style,self.perspective,self.annotations=options(style,perspective,annotations)
        self.export_options=normalize(export_options) if export_options is not None else None
        self.db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True,timeout=30)
        try:
            self.db.execute('BEGIN')
            self.context=PgnContext(self.db,tid)
            self.cursor=self.db.execute('''SELECT official FROM games
                WHERE tid=? AND invalid=0 AND official IS NOT NULL ORDER BY number''',(tid,))
        except BaseException:
            self.db.close();raise

    def chunk(self):
        return ''.join(render_attempt(self.db,r[0],self.style,self.perspective,self.annotations,self.context,export_options=self.export_options)
                       for r in self.cursor.fetchmany(16)).encode('utf-8')

    def close(self):self.db.close()


def preview(path,tid,settings):
    choices=normalize(settings)
    db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True,timeout=30)
    try:
        db.execute('BEGIN');context=PgnContext(db,tid)
        row=db.execute('SELECT official,number FROM games WHERE tid=? AND invalid=0 AND official IS NOT NULL ORDER BY number LIMIT 1',(tid,)).fetchone()
        if not row:return {'pgn':'','game_number':None,'headers':[],'truncated':False}
        text=render_attempt(db,row[0],context=context,export_options=choices)
        import re
        headers=re.findall(r'^\[(\w+) ',text.split('\n\n',1)[0],re.M)
        return {'pgn':text[:100000],'game_number':row[1]+1,'headers':headers,'truncated':len(text)>100000,'characters':len(text)}
    finally:db.close()


async def stream_official(request,path,tid):
    # One ordered reader worker per download; network backpressure limits queued
    # data to one chunk. Cancellation queues close after any in-flight read.
    filetype=request.query.get('filetype','pgn')
    if filetype not in ('pgn','txt'):raise ValueError('Unknown game export file type')
    executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='PgnDownload')
    loop=asyncio.get_running_loop();reader=[]
    annotations=request.query.get('annotations')
    annotations=None if annotations is None else [v for v in annotations.split(',') if v]
    presentation=from_query(request.query)
    def open_reader():reader.append(OfficialPgnReader(path,tid,request.query.get('style','compact'),request.query.get('perspective','engine'),annotations,export_options=presentation))
    def read():return reader[0].chunk()
    def close():
        if reader:reader[0].close()
    try:
        await loop.run_in_executor(executor,open_reader)
        content_type='text/plain' if filetype=='txt' else 'application/x-chess-pgn'
        response=web.StreamResponse(headers={'Content-Type':content_type+'; charset=utf-8',
            'Content-Disposition':f'attachment; filename="official-{tid}.{filetype}"'})
        await response.prepare(request)
        while chunk:=await loop.run_in_executor(executor,read):await response.write(chunk)
        await response.write_eof()
        return response
    finally:
        try:await asyncio.shield(loop.run_in_executor(executor,close))
        finally:executor.shutdown(wait=False)
