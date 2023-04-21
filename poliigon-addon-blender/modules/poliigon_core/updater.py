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

"""Module for general purpose updating for Poliigon software."""

from typing import Dict, Optional, Sequence
from dataclasses import dataclass
import datetime
import json
import threading
import requests


BASE_URL = "https://software.poliigon.com"
TIMEOUT = 20.0

# Status texts
FAIL_GET_VERSIONS = "Failed to get versions"


def v2t(value: str) -> tuple:
    """Take a version string like v1.2.3 and convert it to a tuple."""
    if not value or "." not in value:
        return None
    if value.lower().startswith("v"):
        value = value[1:]
    return tuple([int(ind) for ind in value.split(".")])


def t2v(ver: tuple) -> str:
    """Take a tuple like (2, 80) and construct a string like v2.80."""
    return "v" + ".".join(list(ver))


@dataclass
class VersionData:
    """Container for a single version of the software."""
    version: Optional[tuple] = None
    url: Optional[str] = None
    min_software_version: Optional[tuple] = None  # Inclusive.
    max_software_version: Optional[tuple] = None  # Not inclusive.
    required: Optional[bool] = None
    release_timestamp: Optional[datetime.datetime] = None

    # Internal, huamn readable current status.
    status_title: str = ""
    status_details: str = ""
    status_ok: bool = True

    def update_from_dict(self, data: Dict):
        self.version = v2t(data.get("version"))
        self.url = data.get("url", "")

        # List format like [2, 80]
        self.min_software_version = tuple(data.get("min_software_version"))
        self.max_software_version = tuple(data.get("max_software_version"))
        self.required = data.get("required")
        self.release_timestamp = data.get("release_timestamp")


class SoftwareUpdater():
    """Primary class which implements checks for updates and installs."""

    # Versions of software available.
    stable: Optional[VersionData]
    latest: Optional[VersionData]
    all_versions: Sequence

    # Always initialized
    addon_name: str  # e.g. poliigon-addon-blender.
    addon_version: tuple  # Current addon version.
    software_version: tuple  # DCC software version, e.g. (3, 0).
    base_url: str  # Primary url where updates and version data is hosted.

    # State properties.
    update_ready: Optional[bool] = None  # None until proven true or false.
    update_data: Optional[VersionData] = None
    _last_check: Optional[datetime.datetime] = None
    last_check_callback: Optional[callable] = None  # When last_check changes.
    check_interval: Optional[int] = None  # interval in seconds between auto check.
    verbose: bool = True

    _check_thread: Optional[threading.Thread] = None

    def __init__(self,
                 addon_name: str,
                 addon_version: tuple,
                 software_version: tuple,
                 base_url: Optional[str] = None):
        self.addon_name = addon_name
        self.addon_version = addon_version
        self.software_version = software_version
        self.base_url = base_url if base_url is not None else BASE_URL
        self.current_version = VersionData()

    @property
    def is_checking(self) -> bool:
        """Interface for other modules to see if a check for update running."""
        return self._check_thread and self._check_thread.is_alive()

    @property
    def last_check(self) -> str:
        if not self._last_check:
            return ""
        try:
            return self._last_check.strftime("%Y-%m-%d %H:%M")
        except ValueError as err:
            print("Get last update check error:", err)
            return ""

    @last_check.setter
    def last_check(self, value: str) -> None:
        try:
            self._last_check = datetime.datetime.strptime(
                value, "%Y-%m-%d %H:%M")
        except ValueError as err:
            print("Assign last update check error:", value, err)
            print(err)
            self._last_check = None
        if self.last_check_callback:
            self.last_check_callback(self.last_check)  # The string version.

    def _clear_versions(self) -> None:
        self.stable = None
        self.latest = None
        self.all_versions = []

    def _clear_update(self) -> None:
        self.update_ready = None  # Set to None until proven true or false.
        self.update_data = None
        self.status_ok = True

    def has_time_elapsed(self, hours: int = 24) -> bool:
        """Checks if a given number of hours have passed since last check."""
        now = datetime.datetime.now()
        if not self._last_check:
            return True  # No check on record.
        diff = now - self._last_check
        return diff.total_seconds() / 3600.0 > hours

    def print_debug(self, *args):
        if self.verbose:
            print(*args)

    def update_versions(self) -> None:
        """Fetch the latest versions available from the server."""
        self.status_ok = True  # True until proven false.
        self._clear_versions()
        url = f"{self.base_url}/{self.addon_name}-versions.json"
        res = requests.get(url, timeout=TIMEOUT)

        if not res.ok:
            self.status_title = FAIL_GET_VERSIONS
            self.status_details = (
                "Did not get OK response while fetching available versions "
                f"from {url}")
            self.status_ok = False
            print(self.status_details)
            return
        if res.status_code != 200:
            self.status_title = FAIL_GET_VERSIONS
            self.status_details = (
                "Did not get OK code while fetching available versions")
            self.status_ok = False
            print(self.status_details)
            return

        try:
            resp = json.loads(res.text)
        except json.decoder.JSONDecodeError as e:
            self.status_title = FAIL_GET_VERSIONS
            self.status_details = "Could not parse json response for versions"
            self.status_ok = False
            self.status_is_error = True
            print(self.status_details)
            print(e)
            return

        if resp.get("stable"):
            self.stable = VersionData()
            self.stable.update_from_dict(resp["stable"])
        if resp.get("latest"):
            self.latest = VersionData()
            self.latest.update_from_dict(resp["latest"])
        if resp.get("versions"):
            for itm in resp["versions"]:
                ver = VersionData()
                ver.update_from_dict(itm)
                self.all_versions.append(ver)

        self._last_check = datetime.datetime.now()
        self.last_check = self.last_check  # Trigger callback.

    def check_for_update(self,
                         callback: Optional[callable] = None) -> bool:
        """Fetch and check versions to see if a new update is available."""
        self._clear_update()
        self.update_versions()

        if not self.status_ok:
            if callback:
                callback()
            return False

        # First compare against latest
        if self.stable and self._check_eligible(self.stable):
            self.print_debug(
                "Using latest stable:",
                self.stable.version,
                "vs current addon: ",
                self.addon_version)
            if self.stable.version > self.addon_version:
                self.update_data = self.stable
                self.update_ready = True
            else:
                self.update_ready = False
            if callback:
                callback()
            return True

        # Eligible wasn't present or more eligible, find next best.
        self.print_debug("Unable to use current stable release")
        max_version = self.get_max_eligible()
        if max_version:
            if max_version.version > self.addon_version:
                self.update_data = max_version
                self.update_ready = True
            else:
                self.update_ready = False
        else:
            self.print_debug("No eligible releases found")
            self.update_ready = False

        if callback:
            callback()
        return True

    def _check_eligible(self, version: VersionData) -> bool:
        """Verify if input version is compatible with the current software."""
        eligible = True
        if version.min_software_version:
            if self.software_version < version.min_software_version:
                eligible = False
        elif version.max_software_version:
            # Inclusive so that if max is 3.0, must be 2.99 or lower.
            if self.software_version >= version.max_software_version:
                eligible = False
        return eligible

    def get_max_eligible(self) -> Optional[VersionData]:
        """Find the eligible version with the highest version number."""
        max_eligible = None
        for ver in self.all_versions:
            if not self._check_eligible(ver):
                continue
            elif max_eligible is None:
                max_eligible = ver
            elif ver.version > max_eligible.version:
                max_eligible = ver
        return max_eligible

    def async_check_for_update(self, callback=None):
        """Start a background thread which will check for updates."""
        if self.is_checking:
            return
        self._check_thread = threading.Thread(target=self.check_for_update,
                                              args=(callback,))
        self._check_thread.daemon = True
        self._check_thread.start()
