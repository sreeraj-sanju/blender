# #### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

"""Module for thread management and thread queues for Poliigon software."""

from typing import Dict, List, Optional, Union
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import Future
from enum import Enum
import functools


class PoolKeys(Enum):
    """ Enum for the different ways to label a thread."""
    INTERACTIVE = 0  # Should be the default and highest prempetive order
    PREVIEW_DL = 1  # Preview thumbnails should be second order
    ASSET_DL = 2  # Asset downloads lowest, don't occupy the 'last thread'


class ThreadManager:
    """The class which manages state of the threads.

    ThreadPools are created upon first use.

    Number of threads per pool can be set "globally" upon creation
    of the ThreadPoolManager or per pool, when a pool is used the first time.

    Decorator to be implemented in a class using the ThreadManager.
    Parameters pool and foreground are explained in detail for queue_thread().
    The code expects the ThreadManager instance in a member variable tm.
    Adapt as needed:

    def run_threaded(key_pool: PoolKeys,
                     max_threads: Optional[int] = None,
                     foreground: bool = False) -> callable:
        # Schedule a function to run in a thread of a chosen pool
        def wrapped_func(func: callable) -> callable:
            @functools.wraps(func)
            def wrapped_func_call(self, *args, **kwargs):
                args = (self, ) + args
                return self.tm.queue_thread(func, key_pool, max_threads,
                                            foreground, *args, **kwargs)
            return wrapped_func_call
        return wrapped_func
    """

    max_threads: int  # "global" max_threads, used if not overriden

    thread_pools: Dict[PoolKeys, ThreadPoolExecutor] = {}

    def __init__(self, max_threads: int = 10):
        self.thread_pools = {}
        self.max_threads = max_threads

    def get_pool(self,
                 key_pool: PoolKeys,
                 max_threads: Optional[int] = None,
                 no_create: bool = False
                 ) -> Optional[ThreadPoolExecutor]:
        """Returns the thread pool for a given key.

        If the pool does not exist, yet, it will be created unless
        no_create is set to True, in which case None gets returned.

        No need to call exernally.
        """
        if key_pool in self.thread_pools:
            return self.thread_pools[key_pool]

        if no_create:
            return None

        if max_threads is None:
            max_threads = self.max_threads

        # TODO(Andreas): Either remove or turn into debug print.
        #                Currently print relates to unit test.
        # print(f"### NEW ThreadPoolExecutor: {key_pool} ###")
        tpe = ThreadPoolExecutor(max_workers=max_threads)
        self.thread_pools[key_pool] = tpe
        return tpe

    def queue_thread(self,
                     func: callable,
                     key_pool: Optional[PoolKeys] = None,
                     max_threads: Optional[int] = None,
                     foreground: bool = False,
                     *args, **kwargs) -> Union[Future, any]:
        """Enqueue a function for threaded execution via a thread pool.

        Parameters:
        key_pool: Selects the pool to be used, see PoolKeys enum.
        max_threads: The maximum number of threads can only be set once upon
                     pool's first usage. It can not be changed later on.
        foreground: Set to True to have the function directly executed
                    instead of being submitted to a thread pool.

        Return value:
        Usually the Future belonging to a scheduled thread.
        If foreground option is used, it may actually be anything,
        as the return value of the function gets returned directly.
        """
        if max_threads is None or max_threads <= 0:
            max_threads = self.max_threads

        if key_pool is None:
            key_pool = PoolKeys.INTERACTIVE

        if foreground:
            # With foreground option the function gets called directly
            # NOTE: When using foreground option, the function returns
            #       the return value of the called function instead of a Future
            fut = func(*args, **kwargs)

        else:
            # Create ThreadPoolExecutor, if not already in thread_pools dict
            thread_pool = self.get_pool(key_pool, max_threads)

            # Finally, kick the can
            # Schedule the function for threaded execution
            fut = thread_pool.submit(func, *args, **kwargs)

        return fut

    def shutdown(self,
                 key_pool: Optional[PoolKeys] = None,
                 wait: bool = True) -> None:
        """Shutdown one or all (key_pool=None) ThreadPoolExecutors."""
        if key_pool is None:
            for tpe in self.thread_pools.values():
                # TODO(Andreas): cancel_futures not in Python 3.7,
                #                shutdown(cancel_futures=cancel_futures)
                tpe.shutdown(wait=wait)
            self.thread_pools = {}
        elif key_pool in self.thread_pools:
            self.thread_pools[key_pool].shutdown(wait=wait)
            del self.thread_pools[key_pool]

    def pool_keys(self) -> List[PoolKeys]:
        """Returns a list containing the pool keys of current pools."""
        return list(self.thread_pools.keys())

    def number_of_pools(self) -> int:
        """Returns the number of currently active ThreadPoolExecutors.

        This does NOT mean, these ThreadPoolExecutors are currently
        actively executing threads.
        """
        return len(self.thread_pools)
