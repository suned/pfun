from __future__ import annotations
from typing import Dict, Any, Callable
from concurrent.futures import Executor, Future
from concurrent.futures.process import _rebuild_exc
from multiprocessing import Manager, Queue
from multiprocessing.pool import Pool
from multiprocessing.managers import SyncManager
from threading import Thread
from dataclasses import dataclass
from uuid import uuid4, UUID
from functools import partial
import traceback
from collections import defaultdict


@dataclass(frozen=True)
class Result:
    id: int
    value: Any


@dataclass(frozen=True)
class Error:
    id: int
    traceback: str
    exception: Exception


@dataclass(frozen=True)
class Todo:
    id_: int
    fn: Callable
    args: tuple
    kwargs: dict


@dataclass(frozen=True)
class ProcessPoolExecutorState:
    manager_address: str
    pool: Pool


@dataclass(frozen=True)
class Stop:
    stop_manager: bool = True


def _extract_tb(e: Exception) -> str:
    tb = traceback.format_exception(type(e), e, e.__traceback__)
    tb_as_str = ''.join(tb)
    tb_with_white_space = '\n"""\n%s"""' % tb_as_str
    return tb_with_white_space


class ManagerThread(Thread):
    def __init__(self, result_queue: Queue[Result], futures, manager):
        self.futures = futures
        self.result_queue = result_queue
        self.manager = manager
        self.stop = False
        super().__init__()
    
    def run(self):
        while True:
            try:
                result = self.result_queue.get()
                if isinstance(result, Stop):
                    self.stop = result
                else:
                    future = self.futures.pop(result.id)
                    if isinstance(result, Error):
                        exc = _rebuild_exc(result.exception, result.traceback)
                        future.set_exception(exc)
                    else:
                        future.set_result(result.value)
                self.result_queue.task_done()
                if self.stop and self.result_queue.empty() and len(self.futures) == 0:
                    del self.result_queue
                    if self.stop.stop_manager:
                        self.manager.shutdown()
                        self.manager.join()
                    return
            except EOFError:
                return


class SchedulerThread(Thread):
    def __init__(self, todo_queue, result_queue, pool, futures):
        self.todo_queue = todo_queue
        self.pool = pool
        self.futures = futures
        self.result_queue = result_queue
        self.stop = None
        super().__init__()
    
    def run(self):
        while True:
            try:
                todo = self.todo_queue.get()
                if isinstance(todo, Stop):
                    self.stop = todo
                else:
                    future: Future = self.futures[todo.id_]
                    if not future.cancelled():
                        future.set_running_or_notify_cancel()
                        try:
                            self.pool.apply_async(partial(execute, self.result_queue, todo.id_, todo.fn, *todo.args, **todo.kwargs))
                        except ValueError as e:
                            future.set_exception(e)
                    else:
                        del self.futures[todo.id]
                self.todo_queue.task_done()
                if self.stop and self.todo_queue.empty():
                    self.result_queue.put(self.stop)
                    del self.pool
                    del self.result_queue
                    del self.todo_queue
                    return
            except EOFError:
                return


def execute(result_queue, id, fn, *args, **kwargs):
    try:
        result = fn(*args, **kwargs)
        wrapped_result = Result(id, result)
    except Exception as e:
        tb = _extract_tb(e)
        wrapped_result = Error(id, tb, e)
    result_queue.put(wrapped_result)


class ProcessPoolExecutor(Executor):
    def __init__(self, 
                 max_workers=None,
                 initializer=None, 
                 initargs=(), 
                 *, 
                 max_tasks_per_child=None):
        self.manager = Manager()
        self.pool: Pool = self.manager.Pool(
            processes=max_workers, 
            initializer=initializer,
            initargs=initargs,
            maxtasksperchild=max_tasks_per_child
        )
        self.result_queue: Queue[Result] = self.manager.Queue()
        self.todo_queue = self.manager.Queue()
        self.futures = {}
        self.init_manager_thread()
        self.init_scheduler_thread()
        self.terminated = False
    
    def init_manager_thread(self):
        self.manager_thread = ManagerThread(self.result_queue, self.futures, self.manager)
        self.manager_thread.setDaemon(True)
        self.manager_thread.start()
    
    def init_scheduler_thread(self):
        self.scheduler_thread = SchedulerThread(self.todo_queue, self.result_queue, self.pool, self.futures)
        self.scheduler_thread.setDaemon(True)
        self.scheduler_thread.start()

    def __getstate__(self) -> ProcessPoolExecutorState:
        return ProcessPoolExecutorState(self.manager.address, self.pool)
    
    def __setstate__(self, state: ProcessPoolExecutorState):
        self.manager = SyncManager(address=state.manager_address)
        self.manager.connect()
        self.pool = state.pool
        self.pool._manager = self.manager  # type: ignore
        self.result_queue = self.manager.Queue()  # type: ignore
        self.todo_queue = self.manager.Queue()
        self.futures = {}
        self.terminated = False
        self.init_manager_thread()
        self.init_scheduler_thread()

    def submit(self, fn, *args, **kwargs):
        if self.terminated:
            raise ValueError('Cant submit new tasks after shutdown has been called')
        id_ = uuid4()
        future = Future()
        self.futures[id_] = future
        self.todo_queue.put(Todo(id_, fn, args, kwargs))
        return future

    def shutdown(self, wait=True, *, cancel_futures=False, stop_manager=True):
        self.terminated = True
        if cancel_futures:
            for future in self.futures.values():
                future.cancel()
        self.todo_queue.put(Stop(stop_manager=stop_manager))
        if wait:
            self.scheduler_thread.join()
            self.manager_thread.join()
        # delete refs to queues to allow them to be collected in manager
        del self.todo_queue
        del self.result_queue
        
            

