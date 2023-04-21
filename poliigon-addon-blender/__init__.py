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

bl_info = {
    "name": "Poliigon Addon",
    "author": "Poliigon",
    "version": (1, 3, 2),
    "blender": (2, 80, 0),
    "location": "3D View",
    "description": "Load models, textures, and more from Poliigon and locally",
    "doc_url": "https://help.poliigon.com/en/articles/6342599-poliigon-addon-for-blender?utm_source=blender&utm_medium=addon",
    "tracker_url": "https://help.poliigon.com/en/?utm_source=blender&utm_medium=addon",
    "category": "3D View",
}


if "bpy" in locals():
    import importlib
    importlib.reload(operators)
    importlib.reload(preferences)
    importlib.reload(props)
    importlib.reload(reporting)
    importlib.reload(toolbox)
    importlib.reload(ui)
    importlib.reload(api)
    importlib.reload(env)
    importlib.reload(updater)
else:
    from . import operators
    from . import preferences
    from . import props
    from . import reporting
    from . import toolbox
    from . import ui
    from .modules.poliigon_core import api  # noqa: F401, needed for package import testing.
    from .modules.poliigon_core import env  # noqa: F401, needed for package import testing.
    from .modules.poliigon_core import updater  # noqa: F401, needed for package import testing.

import bpy


def register():
    bver = ".".join([str(x) for x in bpy.app.version])
    aver = ".".join([str(x) for x in bl_info["version"]])

    props.register()
    preferences.register()
    toolbox.register(bl_info)
    reporting.register("blender", bver, aver, toolbox.cTB.env)
    operators.register()
    ui.register()


def unregister():
    # Reverse order of register.
    ui.unregister()
    operators.unregister()
    reporting.unregister()
    toolbox.unregister()
    preferences.unregister()
    props.unregister()


if __name__ == "__main__":
    register()
