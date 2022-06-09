import dill
from pfun.executors import ProcessPoolExecutor, HasProcessPoolExecutor
from pfun.effect import from_cpu_bound_callable
from pfun import Right, Either
import threading
import psutil
import time

def g(sleep=0):
        time.sleep(sleep)
        return 'Done!'


class Modules:
        def __init__(self):
            self.process_pool_executor = ProcessPoolExecutor()


def test_executor_basic_shutdown():
    e = ProcessPoolExecutor(max_workers=1)
    n_threads = len(threading.enumerate())
    p = e.manager._process
    e.shutdown()
    assert n_threads - 2 == len(threading.enumerate())
    assert not p.is_alive()


def f(e: ProcessPoolExecutor):
    fut = e.submit(g, 2)
    return fut.result()


def test_executor_shutdown_in_two_proceses():
    e = ProcessPoolExecutor()
    fut = e.submit(f, e)
    e.shutdown()
    fut.result()


def test_effect_run() -> None:

    def f(m: HasProcessPoolExecutor) -> Either[None, str]:
        time.sleep(5)
        fut = m.process_pool_executor.submit(g)
        return Right(fut.result())
    
    e = from_cpu_bound_callable(f)
    
    m = Modules()
    with m.process_pool_executor:
        assert e.run(m) == 'Done!'
