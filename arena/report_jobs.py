"""Cancellable read-only report processes, isolated from ratings and game saving."""
import asyncio
import contextlib
import multiprocessing
import time
import uuid


def _render(pipe, args):
    try:
        from .ratings import background_priority
        from .i18n import render_report
        from . import engine_readout
        background_priority()
        engine_readout.progress = lambda done, total: pipe.send({'state': 'running', 'done': done, 'total': total})
        pipe.send({'state': 'running', 'done': 0, 'total': 0})
        pipe.send({'state': 'complete', 'html': render_report(*args)})
    except Exception as error:
        with contextlib.suppress(OSError):pipe.send({'state': 'failed', 'error': str(error)})
    finally:pipe.close()


class ReportJobs:
    def __init__(self):
        self.jobs = {}
        self.closed = False
        self.lock = asyncio.Lock()

    async def start(self, *args):
        async with self.lock:return await self._start(*args)

    async def _start(self, *args):
        if self.closed:raise ValueError('Application is closing')
        # One expensive report at a time. A changed selection supersedes the
        # previous read-only calculation; no result or engine process is touched.
        for job in list(self.jobs.values()):
            if job['state'] == 'running':await self.cancel(job['id'])
        while len(self.jobs) >= 2:self.jobs.pop(next(iter(self.jobs)))
        receive, send = multiprocessing.get_context('spawn').Pipe(duplex=False)
        process = multiprocessing.get_context('spawn').Process(target=_render, args=(send, args), daemon=True)
        ident = uuid.uuid4().hex
        job = {'id': ident, 'state': 'running', 'done': 0, 'total': 0, 'started': time.monotonic(),
               'process': process, 'pipe': receive}
        try:process.start()
        except BaseException:receive.close();send.close();raise
        send.close()
        self.jobs[ident] = job
        job['task'] = asyncio.create_task(self._watch(job))
        return self.status(ident)

    async def _watch(self, job):
        pipe, process = job['pipe'], job['process']
        try:
            while job['state'] == 'running':
                # recv can be large for all-engine HTML; keep it off the clocks.
                if await asyncio.to_thread(pipe.poll, .15):
                    message = await asyncio.to_thread(pipe.recv)
                    job.update(message)
                elif not process.is_alive():
                    raise RuntimeError('Report process ended before returning a report')
        except asyncio.CancelledError:raise
        except (OSError, EOFError, RuntimeError) as exc:
            if job['state'] == 'running':job.update(state='failed', error=str(exc))
        finally:
            if process.is_alive() and job['state'] != 'complete':process.terminate()
            await asyncio.to_thread(process.join, 3)
            if process.is_alive():process.kill();await asyncio.to_thread(process.join, 3)
            pipe.close()

    def status(self, ident):
        if ident not in self.jobs:raise ValueError('Report request is no longer available')
        job = self.jobs[ident]
        return {k: v for k, v in job.items() if k not in ('process', 'pipe', 'task', 'started')} | {'elapsed': time.monotonic()-job['started']}

    async def cancel(self, ident):
        job = self.jobs.get(ident)
        if job and job['state'] == 'running':
            job['state'] = 'cancelled'
            if job['process'].is_alive():job['process'].terminate()
            await job['task']

    async def render(self, *args):
        status = await self.start(*args)
        job = self.jobs[status['id']]
        await job['task']
        if job['state'] != 'complete':raise ValueError(job.get('error', 'Report cancelled'))
        return job['html']

    async def close(self):
        async with self.lock:
            self.closed = True
            for ident in list(self.jobs):await self.cancel(ident)
