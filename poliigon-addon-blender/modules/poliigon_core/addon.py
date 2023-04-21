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

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import lru_cache
from typing import Dict, List, Optional, Sequence
import functools
import os
import time

from . import api
from . import env
from . import settings
from . import updater
from . import thread_manager as tm
from . import asset_index
from .assets import AssetType, SIZES


DOWNLOAD_POLL_INTERVAL = 0.25
MAX_DOWNLOAD_RETRIES = 10
MAX_PARALLEL_ASSET_DOWNLOADS = 2
MAX_PARALLEL_DOWNLOADS_PER_ASSET = 8
SIZE_DEFAULT_POOL = 10


class SubscriptionState(Enum):
    """Values for allowed user subscription states."""
    NOT_POPULATED = 0
    FREE = 1,
    ACTIVE = 2,
    PAUSED = 3,
    CANCELLED = 4


@dataclass
class PoliigonSubscription:
    """Container object for a subscription."""

    plan_name: Optional[str] = None
    plan_credit: Optional[int] = None
    next_credit_renewal_date: Optional[datetime] = None
    next_subscription_renewal_date: Optional[datetime] = None
    is_free_user: Optional[bool] = None
    subscription_state: Optional[SubscriptionState] = SubscriptionState.NOT_POPULATED


@dataclass
class PoliigonUser:
    """Container object for a user."""

    user_name: str
    user_id: int
    credits: Optional[int] = None
    credits_od: Optional[int] = None
    plan: Optional[PoliigonSubscription] = None


class PoliigonAddon():
    """Poliigon addon used for creating base singleton in DCC applications."""

    addon_name: str  # e.g. poliigon-addon-blender
    addon_version: tuple  # Current addon version
    software_source: str  # e.g. blender
    software_version: tuple  # DCC software version, e.g. (3, 0)

    library_paths: Sequence = []

    download_queue: Dict = {}
    purchase_queue: Dict = {}

    def __init__(self,
                 addon_name: str,
                 addon_version: tuple,
                 software_source: str,
                 software_version: tuple,
                 addon_env: env.PoliigonEnvironment,
                 addon_settings: settings.PoliigonSettings):
        self.addon_name = addon_name
        self.addon_version = addon_version
        self.software_source = software_source
        self.software_version = software_version

        self.user = None
        self.login_error = None

        self.purchase_queue = {}
        self.download_cancelled = set()
        self.download_queue = {}

        self._env = addon_env
        self._settings = addon_settings
        self._api = api.PoliigonConnector(
            env=self._env,
            software=software_source
        )
        self._api.register_update(
            ".".join([str(x) for x in addon_version]),
            ".".join([str(x) for x in software_version])
        )
        self._updater = updater.SoftwareUpdater(
            addon_name=addon_name,
            addon_version=addon_version,
            software_version=software_version
        )
        self._tm = tm.ThreadManager()

        self.settings_config = self._settings.config

        base_dir = os.path.join(
            os.path.expanduser("~"),
            "Poliigon"
        )

        default_lib_path = os.path.join(base_dir, "Library")
        self.library_paths.append(default_lib_path)

        default_asset_index_path = os.path.join(
            base_dir,
            "AssetIndex",
            "asset_index.json",
        )
        self._asset_index = asset_index.AssetIndex(
            path_cache=default_asset_index_path)

        self.online_previews_path = os.path.join(base_dir, "OnlinePreviews")
        if not os.path.exists(self.online_previews_path):
            try:
                os.makedirs(self.online_previews_path)
            except Exception as e:
                print("Failed to create directory: ", e)

    # Decorator copied from comment in thread_manager.py
    def run_threaded(key_pool: tm.PoolKeys,
                     max_threads: Optional[int] = None,
                     foreground: bool = False) -> callable:
        """Schedule a function to run in a thread of a chosen pool"""
        def wrapped_func(func: callable) -> callable:
            @functools.wraps(func)
            def wrapped_func_call(self, *args, **kwargs):
                args = (self, ) + args
                return self._tm.queue_thread(func, key_pool,
                                             max_threads, foreground,
                                             *args, **kwargs)
            return wrapped_func_call
        return wrapped_func

    def is_logged_in(self) -> bool:
        """Returns whether or not the user is currently logged in."""
        return self._api.token is not None and not self._api.invalidated

    def is_user_invalidated(self) -> bool:
        """Returns whether or not the user token was invalidated."""
        return self._api.invalidated

    def clear_user_invalidated(self):
        """Clears any invalidation flag for a user."""
        self._api.invalidated = False

    @run_threaded(tm.PoolKeys.INTERACTIVE)
    def log_in_with_credentials(self, email: str, password: str):
        self.clear_user_invalidated()

        req = self._api.log_in(
            email,
            password
        )

        if req.ok:
            data = req.body

            self.user = PoliigonUser(
                user_name=data["user"]["name"],
                user_id=data["user"]["id"]
            )

            self.login_error = None
        else:
            self.login_error = req.error

        return req

    def log_in_with_website(self):
        pass

    @run_threaded(tm.PoolKeys.INTERACTIVE)
    def log_out(self):
        req = self._api.log_out()
        if req.ok:
            print("Logout success")
        else:
            print(req.error)

        self._api.token = None

        # Clear out user on logout.
        self.user = None

    def add_library_path(self, path: str, primary: bool = True):
        if not os.path.isdir(path):
            print("Path is not a directory!")
            return
        elif path in self.library_paths:
            print("Path already exists!")
            return

        if self.library_paths and primary:
            self.library_paths[0] = path
        else:
            self.library_paths.append(path)

    def get_library_path(self, primary: bool = True):
        if self.library_paths and primary:
            return self.library_paths[0]
        elif len(self.library_paths) > 1:
            # TODO(Mitchell): Return the most relevant lib path based on some input (?)
            return None
        else:
            return None

    @run_threaded(tm.PoolKeys.INTERACTIVE)
    def get_credits(self):
        req = self._api.get_user_balance()

        if req.ok:
            data = req.body
            self.user.credits = data.get("subscription_balance")
            self.user.credits_od = data.get("ondemand_balance")
        else:
            self.user.credits = None
            self.user.credits_od = None
            print(req.error)

    @run_threaded(tm.PoolKeys.INTERACTIVE)
    def get_subscription_details(self):
        """Fetches the current user's subscription status."""
        req = self._api.get_subscription_details()

        subscription = PoliigonSubscription()
        if req.ok:
            plan = req.body
            if plan.get("plan_name") and plan["plan_name"] != api.STR_NO_PLAN:
                subscription.plan_name = plan["plan_name"]
                subscription.plan_credit = plan.get("plan_credit", None)

                # Extract "2022-08-19" from "2022-08-19 23:58:37"
                renew = plan.get("next_subscription_renewal_date", "")
                try:
                    renew = datetime.strptime(renew, "%Y-%m-%d %H:%M:%S")
                    subscription.next_subscription_renewal_date = renew
                except ValueError:
                    subscription.next_subscription_renewal_date = None

                next_credits = plan.get("next_credit_renewal_date", "")
                try:
                    next_credits = datetime.strptime(
                        next_credits,
                        "%Y-%m-%d %H:%M:%S"
                    )
                    subscription.next_credit_renewal_date = next_credits
                except ValueError:
                    subscription.next_credit_renewal_date = None

                # TODO: Determine the state of the subscription.
                subscription.subscription_state = SubscriptionState.ACTIVE

                subscription.is_free_user = False
            else:
                subscription.plan_name = None
                subscription.plan_credit = None
                subscription.next_subscription_renewal_date = None
                subscription.next_credit_renewal_date = None
                subscription.is_free_user = True
                subscription.subscription_state = SubscriptionState.FREE
        else:
            subscription.subscription_state = SubscriptionState.NOT_POPULATED
            print(req.error)

        if self.user is not None:
            self.user.plan = subscription

    def is_purchase_queued(self, asset_id):
        """Checks if an asset is queued for purchase"""
        queued = asset_id in self.purchase_queue.keys()
        return queued

    # TODO: Enclose the following func in a thread lock.
    def queue_purchase(self, asset_data, search, category):
        """Enqueue purchase request and return the Future object"""
        print(f"Queued asset for purchase{asset_data.asset_id}")
        future = self.purchase_asset(asset_data, search, category)
        self.purchase_queue[asset_data.asset_id] = future

        return future

    @run_threaded(tm.PoolKeys.INTERACTIVE)
    def purchase_asset(self, asset_data, search, category):
        """Create a thread to purchase an asset"""
        req = self._api.purchase_asset(asset_data.asset_id, search, category)
        
        # TODO: Enclose the following del line in a thread lock.
        del self.purchase_queue[asset_data.asset_id]

        if req.ok:
            print(f"Purchased asset {asset_data.asset_id}")
            self._asset_index.mark_purchased(asset_data.asset_id)
        else:
            print(f"Failed to purchase asset {asset_data.asset_id}", str(req.error), str(req.body))

        return req.ok

    def get_thumbnail_path(self, asset_name, index):
        """Return the best fitting thumbnail preview for an asset.

        The primary grid UI preview will be named asset_preview1.png,
        all others will be named such as asset_preview1_1K.png
        """
        if index == 0:
            # 0 is the small grid preview version of _preview1.

            # Fallback to legacy option of .jpg files if .png not found.
            thumb = os.path.join(
                self.online_previews_path,
                asset_name + "_preview1.png"
            )
            if not os.path.exists(thumb):
                thumb = os.path.join(
                    self.online_previews_path,
                    asset_name + "_preview1.jpg"
                )
        else:
            thumb = os.path.join(
                self.online_previews_path,
                asset + f"_preview{index}_1K.png")
        return thumb

    def is_download_queued(self, asset_id):
        """Checks if an asset is queued for download"""
        cancelled = asset_id in self.download_cancelled
        queued = asset_id in self.download_queue.keys()
        return queued and not cancelled

    def should_continue_asset_download(self, asset_id):
        """Check for any user cancel presses."""
        return asset_id not in self.download_cancelled

    def update_asset_data(self,
                          asset_id,
                          download_dir,
                          primary_files,
                          add_files):
        dbg = 1
        self.print_debug("update_asset_data", dbg=dbg)
        if not os.path.exists(download_dir):
            self.print_debug("update_asset_data NO DIR", dbg=dbg)
            return
        asset_files = []
        for path, dirs, files in os.walk(download_dir):
            asset_files += [os.path.join(path, file) for file in files if not file.endswith(api.DOWNLOAD_TEMP_SUFFIX)]
        if len(asset_files) == 0:
            self.print_debug("update_asset_data NO FILES", dbg=dbg)
            return
        # Ensure previously found asset files are added back
        asset_files += primary_files + add_files
        asset_files = list(set(asset_files))
        self._asset_index.update_from_directory(asset_id, download_dir)
        self.print_debug("update_asset_data DONE", dbg=dbg)

    def queue_download(self, asset_data, size=None):
        """Enqueue download request and return the Future object"""
        print(f"Queued asset {asset_data.asset_id} for download!")

        self.download_queue[asset_data.asset_id] = {
            "data": asset_data,
            "size": size,
            "download_size": None
        }

        future = self.download_asset(asset_data, size)
        self.download_queue[asset_data.asset_id]["future"] = future

        return future

    @run_threaded(tm.PoolKeys.ASSET_DL, MAX_PARALLEL_ASSET_DOWNLOADS)
    def download_asset(self, asset_data, size):
        """Create a thread to download an asset"""
        dbg = True
        asset_id = asset_data.asset_id
        asset_name = asset_data.asset_name
        asset_type = asset_data.asset_type

        # A queued download (user started more than MAX_PARALLEL_ASSET_DOWNLOADS)
        # may have been cancelled again before we reach this point
        user_cancel = asset_id in self.download_cancelled
        if user_cancel:
            # self.print_debug("download_asset_thread CANCEL BEFORE START", dbg=dbg)
            del self.download_queue[asset_id]
            self.download_cancelled.remove(asset_id)
            return
        if asset_id not in self.download_queue:
            # self.print_debug("download_asset_thread DOWNLOAD NOT QUEUED", dbg=dbg)
            return

        t_start = time.monotonic()

        asset_size = self.download_queue[asset_id]['size']
        asset_data = self.download_queue[asset_id]['data']

        download_data = self.get_download_data(asset_data, size=asset_size)
        self.print_debug("download_asset_thread", download_data, dbg=dbg)

        library_dir, primary_files, add_files = self.get_destination_library_directory(asset_data)
        download_dir = os.path.join(library_dir, asset_data.asset_name)
        if not os.path.exists(download_dir):
            os.mkdir(download_dir)

        self.print_debug(f"download_asset_thread downloading to: {download_dir}")

        tpe = ThreadPoolExecutor(max_workers=MAX_PARALLEL_DOWNLOADS_PER_ASSET)

        size_asset = 0
        retries = MAX_DOWNLOAD_RETRIES
        all_done = False
        user_cancel = False

        self.print_debug("download_asset_thread LOOP", dbg=dbg)
        while not all_done and not user_cancel and retries > 0:
            user_cancel = not self.download_update(asset_id, 1, 0.001)  # Init progress bar

            t_start_urls = time.monotonic()
            dl_list, size_asset = self.get_download_list(asset_id,
                                                         download_data)
            t_end_urls = time.monotonic()
            duration_urls = t_end_urls - t_start_urls

            user_cancel = not self.download_update(asset_id, 1, 0.001)
            if user_cancel:
                self.print_debug("download_asset_thread USER CANCEL", dbg=dbg)
                break
            elif dl_list is None:
                self.print_debug("download_asset_thread URL RETRIEVE -> no downloads", dbg=dbg)
                retries -= 1
                continue  # retry

            self.print_debug(f"=== Requesting URLs took {duration_urls:.3f} s.", dbg=dbg)

            self.schedule_downloads(tpe, dl_list, download_dir)

            self.print_debug("download_asset_thread POLL LOOP", dbg=dbg)
            while not all_done and not user_cancel:
                time.sleep(DOWNLOAD_POLL_INTERVAL)
                all_done, any_error, size_downloaded = self.check_downloads(dl_list)

                # Get user cancel and update progress UI
                percent_downloaded = max(size_downloaded / size_asset, 0.001)
                user_cancel = not self.download_update(asset_id,
                                                       size_asset,
                                                       percent_downloaded)
                if all_done and not any_error:
                    self.print_debug("download_asset_thread ALL DONE", dbg=dbg)
                    retries = 0
                    break
                elif any_error or user_cancel:
                    self.print_debug("download_asset_thread CANCELLING", dbg=dbg)
                    # TODO(Andreas): If cancelling due to expired link error,
                    #                maybe the DOWNLOADING ones should be
                    #                allowed to finish first
                    self.cancel_downloads(dl_list)
                    break
            retries -= 1

        # TODO(Andreas): what if retries exhausted?
        #                I'd probably opt for opening some error requester

        if all_done and not any_error and not user_cancel:
            self.rename_downloads(dl_list)

        self.update_asset_data(asset_id, download_dir,
                               primary_files, add_files)
        self.print_debug("download_asset_thread REMOVE FROM DL QUEUE", dbg=dbg)
        try:
            del self.download_queue[asset_id]
        except KeyError:
            pass  # Already removed.
        try:
            self.download_cancelled.remove(asset_id)
        except KeyError:
            pass  # Already removed or never existed.

        # Don't even think about using refresh_UI(),
        # we are in thread context here!
        # self.vRedraw = 1

        t_end = time.monotonic()
        if all_done and not any_error and not user_cancel:
            duration = t_end - t_start
            size_MB = size_asset / (1024 * 1024)
            speed = size_MB / duration
            self.print_debug(f"=== Successfully downloaded {asset_name}", dbg=dbg)
            self.print_debug(f"    ENTIRE ASSET : {size_MB:.2f} MB, {duration:.3f} s, {speed:.2f} MB/s", dbg=dbg)
            for download in dl_list:
                size_MB = download.size_downloaded / (1024 * 1024)
                speed = size_MB / download.duration
                self.print_debug(f"    {download.filename} : {size_MB:.2f} MB, {download.duration:.3f} s, {speed:.2f} MB/s", dbg=dbg)

        return True

    def download_update(self, asset_id, download_size, download_percent=0.001):
        """Updates info for download progress bar, return false to cancel."""
        if asset_id in self.download_queue.keys():
            self.download_queue[asset_id]['download_size'] = download_size
            self.download_queue[asset_id]['download_percent'] = download_percent
        # self.refresh_ui()
        return self.should_continue_asset_download(asset_id)

    def get_destination_library_directory(self, asset_data):
        # Usually the asset will be downloaded into the primary library.
        # Exception: There are already files for this asset located in another
        #            library (and only in this, _not_ in primary).
        dbg = 0
        self.print_debug("get_destination_library_directory", dbg=dbg)
        asset_name = asset_data.asset_name
        asset_type = asset_data.asset_type

        library_dir = self.get_library_path()
        primary_files = []
        add_files = []
        if not asset_data.is_local:
            return library_dir, primary_files, add_files

        for file in self._asset_index.get_files(asset_data.asset_id).keys():
            if not os.path.exists(file):
                continue
            if file.split(asset_name, 1)[0] == library_dir:
                primary_files.append(file)
            else:
                add_files.append(file)

        self.print_debug(0, "get_destination_library_directory",
                         "Found asset files in primary library:",
                         primary_files)

        if len(primary_files) == 0 and len(add_files) > 0:
            # Asset must be located in an additional directory
            #
            # Always download new maps to the highest-level directory
            # containing asset name, regardless of any existing (sub)
            # structure within that directory
            file = add_files[0]
            if asset_name in os.path.dirname(file):
                library_dir = file.split(asset_name, 1)[0]
                self.print_debug(1,
                                 "get_destination_library_directory",
                                 library_dir)

        self.print_debug("get_destination_library_directory DONE", dbg=dbg)
        return library_dir, primary_files, add_files

    def get_download_data(self, asset_data, size=None):
        """Construct the data needed for the download.

        Args:
            asset_data: Original asset data structure.
            size: Intended download size like '4K', fallback to pref default.
        """
        dbg = True

        type_data = asset_data.get_type_data()
        sizes_data = type_data.get_size_list()
        workflow = type_data.get_workflow()

        self.print_debug("get_download_data", "asset_data", asset_data, dbg=dbg)
        self.print_debug("get_download_data", "type_data", type_data, dbg=dbg)
        self.print_debug("get_download_data", "sizes_data", sizes_data, dbg=dbg)
        self.print_debug("get_download_data", "workflow", workflow, dbg=dbg)

        download_data = {
            'assets': [
                {
                    'id': asset_data.asset_id,
                    'name': asset_data.asset_name
                }
            ]
        }

        sizes = [size]

        if size in ['', None]:
            if asset_data.asset_type == AssetType.TEXTURE:
                sizes = [self.settings_config.get("download", "tex_res")]
            elif asset_data.asset_type == AssetType.MODEL:
                sizes = [self.settings_config.get("download", "model_res")]
            elif asset_data.asset_type == AssetType.HDRI:
                sizes = [self.settings_config.get("download", "hdri_bg")]
            elif asset_data.asset_type == AssetType.BRUSH:
                sizes = [self.settings_config.get("download", "brush")]

            self.download_queue[asset_data.asset_id]['size'] = sizes[0]

        if asset_data.asset_type in [AssetType.HDRI, AssetType.TEXTURE]:
            map_codes = type_data.get_map_type_code_list(workflow)

            download_data['assets'][0]['workflows'] = [workflow]
            download_data['assets'][0]['type_codes'] = map_codes

        elif asset_data.asset_type == AssetType.MODEL:
            download_data['assets'][0]['lods'] = int(
                self.settings_config.getboolean("download", "download_lods"))
            download_data['assets'][0]['softwares'] = ['ALL_OTHERS']

        elif asset_data.asset_type == AssetType.BRUSH:
            # No special data needed for Brushes
            pass

        download_data['assets'][0]['sizes'] = [
            size for size in sizes if size in sizes_data]
        if not len(download_data['assets'][0]['sizes']):
            for size in reversed(SIZES):
                if size in sizes_data:
                    download_data['assets'][0]['sizes'] = [size]
                    break
        if not download_data['assets'][0]['sizes']:
            msg = "Missing sizes for download! Setting size to minimum value."
            download_data['assets'][0]['sizes'] = [SIZE[0]]
            self.print_debug(msg, dbg=dbg)

        return download_data

    def get_download_list(self,
                          asset_id,
                          download_data) -> Optional[List[api.FileDownload]]:
        dl_list = None
        size_asset = 0
        res = self._api.download_asset_get_urls(asset_id, download_data)
        if res.ok:
            dl_list = res.body.get("downloads", None)
            size_asset = res.body.get("size_asset", 0)
            if len(dl_list) == 0:
                pass
                print("get_download_list Empty download list despite success")
        else:
            pass
            # Error is handled outside, including retries
            print("get_download_list URL retrieve error")

        # self.print_debug("get_download_list DONE", dbg=dbg)
        return dl_list, size_asset

    def schedule_downloads(self, tpe, dl_list, directory):
        dbg = True
        self.print_debug("schedule_downloads", dbg=dbg)
        dl_list.sort(key=lambda dl: dl.size_expected)

        for download in dl_list:
            download.directory = directory
            # Andreas: Could also check here, if already DONE and not start
            #          the thread at all.
            #          Yet, I decided to prefer it handled by the thread itself.
            #          In this way the flow is always identical.
            download.status = api.DownloadStatus.WAITING
            self.print_debug("schedule_downloads SUBMIT %s", download.filename, dbg=dbg)
            download.fut = tpe.submit(self._api.download_asset_file,
                                      download=download)
        self.print_debug("schedule_downloads DONE", dbg=dbg)

    def check_downloads(self, dl_list):
        any_error = False
        all_done = True
        size_downloaded = 0
        self.print_debug(dl_list, dbg=True)
        for download in dl_list:
            size_downloaded += download.size_downloaded

            fut = download.fut
            if not fut.done():
                all_done = False
            else:
                res = fut.result()
                had_excp = fut.exception() is not None
                self.print_debug(fut.exception(), dbg=True)
                if not res.ok or had_excp:
                    any_error = True
                    all_done = False
                    break
        return all_done, any_error, size_downloaded

    def cancel_downloads(self, dl_list):
        dbg = True
        # cancel all download threads
        self.print_debug("cancel_downloads", dbg=dbg)
        for download in dl_list:
            download.set_status_cancelled()
            download.fut.cancel()
        # wait for threads to actually return
        self.print_debug("cancel_downloads WAITING", dbg=dbg)
        for download in dl_list:
            if download.fut.cancelled():
                continue
            try:
                download.fut.result(timeout=60)
            except concurrent.futures.TimeoutError:
                # TODO(Andreas): Now there seems to be some real issue...
                raise
            except BaseException as err:
                # The following line only works in Python 3.8+
                # self.print_debug(f"Unexpected {err=}, {type(err)=}", dbg=dbg)
                self.print_debug(f"Unexpected err={err}, type(err)={type(err)}", dbg=dbg)
                raise
        self.print_debug("cancel_downloads DONE", dbg=dbg)

    def rename_downloads(self, dl_list):
        dbg = False
        self.print_debug("rename_downloads", dbg=dbg)
        for download in dl_list:
            if download.status != api.DownloadStatus.DONE:
                self.print_debug("rename_downloads ALL DONE and still not DONE!!!", dbg=dbg)
            path_temp = download.get_path(temp=True)
            path_final = download.get_path(temp=False)
            if os.path.exists(path_temp):
                os.rename(path_temp, path_final)
            elif os.path.exists(path_final):
                pass # nothing to do
            else:
                self.print_debug("Nobody ever wanted to be here", dbg=dbg)
        self.print_debug("rename_downloads DONE", dbg=dbg)

    def print_debug(self, *args, dbg=False, bg=True):
        """Print out a debug statement with no separator line.

        Cache based on args up to a limit, to avoid excessive repeat prints.
        All args must be flat values, such as already casted to strings, else
        an error will be thrown.
        """
        if dbg:
            # Ensure all inputs are hashable, otherwise lru_cache fails.
            stringified = [str(arg) for arg in args]
            self._cached_print(*stringified, bg=bg)

    @lru_cache(maxsize=32)
    def _cached_print(self, *args, bg: bool):
        """A safe-to-cache function for printing."""
        print(*args)
