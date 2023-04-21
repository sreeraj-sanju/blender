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


from bpy.props import (
    FloatProperty,
    PointerProperty,
    StringProperty,
)
import bpy.utils.previews


class PoliigonUserProps(bpy.types.PropertyGroup):
    vEmail: StringProperty(
        name="", description="Your Email", options={"SKIP_SAVE"}
    )
    vPassShow: StringProperty(
        name="", description="Your Password", options={"SKIP_SAVE"}
    )
    vPassHide: StringProperty(
        name="",
        description="Your Password",
        options={"HIDDEN","SKIP_SAVE"},
        subtype="PASSWORD",
    )
    search_poliigon: StringProperty(
        name="",
        default="",
        description="Search Poliigon Assets",
        options={"SKIP_SAVE"},
    )
    search_my_assets: StringProperty(
        name="",
        default="",
        description="Search My Assets",
        options={"SKIP_SAVE"},
    )
    search_imported: StringProperty(
        name="",
        default="",
        description="Search Imported Assets",
        options={"SKIP_SAVE"},
    )


def register():
    bpy.utils.register_class(PoliigonUserProps)
    bpy.types.WindowManager.poliigon_props = PointerProperty(
        type=PoliigonUserProps
    )

    bpy.types.Scene.vEditText = StringProperty(default="")
    bpy.types.Scene.vEditMatName = StringProperty(default="")
    bpy.types.Scene.vDispDetail = FloatProperty(default=1.0, min=0.1, max=10.0)

    bpy.types.Material.poliigon = StringProperty(default="", options={"HIDDEN"})
    bpy.types.Object.poliigon = StringProperty(default="", options={"HIDDEN"})
    bpy.types.Object.poliigon_lod = StringProperty(default="", options={"HIDDEN"})
    bpy.types.Image.poliigon = StringProperty(default="", options={"HIDDEN"})

    bpy.context.window_manager.poliigon_props.vEmail = ""
    bpy.context.window_manager.poliigon_props.vPassShow = ""
    bpy.context.window_manager.poliigon_props.vPassHide = ""
    bpy.context.window_manager.poliigon_props.search_poliigon = ""
    bpy.context.window_manager.poliigon_props.search_my_assets = ""
    bpy.context.window_manager.poliigon_props.search_imported = ""


def unregister():
    bpy.utils.unregister_class(PoliigonUserProps)
    del bpy.types.WindowManager.poliigon_props

    del bpy.types.Scene.vEditText
    del bpy.types.Scene.vEditMatName
    del bpy.types.Scene.vDispDetail
