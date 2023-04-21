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

import os

import bpy

from .toolbox import cTB
from . import reporting

THUMB_SIZES = ["Tiny", "Small", "Medium", "Large", "Huge"]


def optin_update(self, context):
    """Update the optin settings."""
    prefs = bpy.context.preferences.addons.get(__package__, None)
    reporting.set_optin(prefs.preferences.reporting_opt_in)


def verbose_update(self, context):
    """Clear out print cache, which could prevent new, near-term prinouts."""
    cTB._cached_print.cache_clear()


def get_preferences_width(context):
    """Get the width of the user preferences draw area."""
    for area in context.screen.areas:
        if area.type == "PREFERENCES":
            for vR in area.regions:
                if vR.type == "WINDOW":
                    vWidth = vR.width - 25 - 20
                    return vWidth
    return None


def f_BuildSettings(self, context):
    dbg = 0
    cTB.print_separator(dbg, "f_BuildSettings")

    cTB._api._mp_relevant = True  # flag in request's meta data for Mixpanel

    pwidth = get_preferences_width(context)

    vBox = self.layout.box().column()

    vCol = vBox.column()

    vCol.label(text="Library :")

    vOp = vCol.operator(
        "poliigon.poliigon_library",
        icon="FILE_FOLDER",
        text=cTB.vSettings["library"],
    )
    vOp.vMode = "update_library"
    vOp.directory = cTB.vSettings["library"]
    vOp.vTooltip = "Set Default Poliigon Library Directory"

    if not os.path.exists(cTB.vSettings["library"]):
        vCol.label(text="(Poliigon Library not set.)", icon="ERROR")
        return

    vCol.separator()

    # ADDITIONAL DIRS .........................................................

    vBox = self.layout.box()

    vOp = vBox.operator(
        "poliigon.poliigon_setting",
        text=str(len(cTB.vSettings["add_dirs"])) + "  Additional Directories",
        icon="DISCLOSURE_TRI_DOWN"
        if cTB.vSettings["show_add_dir"]
        else "DISCLOSURE_TRI_RIGHT",
        emboss=0,
    )
    vOp.vMode = "show_add_dir"
    if cTB.vSettings["show_add_dir"]:
        vOp.vTooltip = "Hide Additional Directories"
    else:
        vOp.vTooltip = "Show Additional Directories"

    if cTB.vSettings["show_add_dir"]:
        vCol = vBox.column()

        for vDir in cTB.vSettings["add_dirs"]:
            vRow = vCol.row(align=1)
            vCheck = vDir not in cTB.vSettings["disabled_dirs"]
            vOp = vRow.operator(
                "poliigon.poliigon_setting",
                text="",
                depress=vCheck,
                emboss=False,
                icon="CHECKBOX_HLT" if vCheck else "CHECKBOX_DEHLT",
            )
            vOp.vMode = "disable_dir_" + vDir
            if vCheck:
                vOp.vTooltip = "Disable Additional Directory"
            else:
                vOp.vTooltip = "Enable Additional Directory"

            vRow.label(text=vDir)

            vOp = vRow.operator("poliigon.poliigon_setting", text="", icon="TRASH")
            vOp.vMode = "del_dir_" + vDir
            vOp.vTooltip = "Remove Additional Directory"

            vCol.separator()

        vRow = vCol.row(align=1)
        vOp = vRow.operator(
            "poliigon.poliigon_directory",
            text="Add Additional Directory",
            icon="ADD",
        )
        vOp.directory = cTB.vSettings["library"]
        vOp.vTooltip = "Add Additional Asset Directory"

        vCol.separator()

    # DISPLAY PREFS............................................................

    vBox = self.layout.box()

    vOp = vBox.operator(
        "poliigon.poliigon_setting",
        text="Display Preferences",
        icon="DISCLOSURE_TRI_DOWN"
        if cTB.vSettings["show_display_prefs"]
        else "DISCLOSURE_TRI_RIGHT",
        emboss=0,
    )
    vOp.vMode = "show_display_prefs"
    if cTB.vSettings["show_display_prefs"]:
        vOp.vTooltip = "Hide Display Preferences"
    else:
        vOp.vTooltip = "Show Display Preferences"

    if cTB.vSettings["show_display_prefs"]:
        vCol = vBox.column()

        vCol.label(text="Thumbnail Size :")
        vRow = vCol.row(align=False)
        for size in THUMB_SIZES:
            vOp = vRow.operator(
                "poliigon.poliigon_setting",
                text=size,
                depress=cTB.vSettings["thumbsize"] == size,
            )
            vOp.vMode = f"thumbsize@{size}"
            vOp.vTooltip = f"Show {size} Thumbnails"

        vCol.separator()

        vCol.label(text="Assets Per Page :")
        vRow = vCol.row(align=False)
        for vN in [6, 8, 10, 20]:
            vOp = vRow.operator(
                "poliigon.poliigon_setting",
                text=str(vN),
                depress=cTB.vSettings["page"] == vN,
            )
            vOp.vMode = "page@" + str(vN)
            vOp.vTooltip = "Show " + str(vN) + " Assets per Page"

        vRow = vCol.row()
        vRow.scale_y = 0.25
        vRow.label(text="")
        vRow = vCol.row()
        vSplit = vRow.split(factor=0.76)
        vSplitCol = vSplit.column()
        vSplitCol.label(
            text="Press Refresh Data to reload icons and reset addon data:")
        vSplitCol = vSplit.column()
        vSplitCol.operator(
            "poliigon.refresh_data",
            icon="FILE_REFRESH")

        vCol.separator()

    # DOWNLOAD PREFS ..........................................................

    vDownloadCol = self.layout.column(align=1)
    vBox = vDownloadCol.box()

    vOp = vBox.operator(
        "poliigon.poliigon_setting",
        text="Asset Preferences",
        icon="DISCLOSURE_TRI_DOWN"
        if cTB.vSettings["show_default_prefs"]
        else "DISCLOSURE_TRI_RIGHT",
        emboss=0,
    )
    vOp.vMode = "show_default_prefs"
    if cTB.vSettings["show_default_prefs"]:
        vOp.vTooltip = "Hide Download Preferences"
    else:
        vOp.vTooltip = "Show Download Preferences"

    if cTB.vSettings["show_default_prefs"]:
        vCol = vBox.column()

        vCol.label(text="Default Texture Resolution :")
        vPGrid = vCol.grid_flow(
            row_major=1,
            columns=int((pwidth - 20) / 40),
            even_columns=1,
            even_rows=1,
            align=0,
        )
        for vS in ["1K", "2K", "3K", "4K", "6K", "8K", "16K"]:
            vOp = vPGrid.operator(
                "poliigon.poliigon_setting",
                text=vS,
                depress=(vS in cTB.vSettings["res"]),
            )
            vOp.vMode = "default_res_" + vS
            vOp.vTooltip = "The default Resolution to use for Texture Assets"

        vCol.separator()

        # .....................................................................

        vCol = vDownloadCol.box().column()

        vCol.separator()

        vRow = vCol.row(align=1)
        vRow.separator()
        vOp = vRow.operator(
            "poliigon.poliigon_setting",
            text="",
            depress=cTB.vSettings["download_prefer_blend"],
            emboss=False,
            icon="CHECKBOX_HLT" if cTB.vSettings["download_prefer_blend"] else "CHECKBOX_DEHLT",
        )
        vOp.vMode = "download_prefer_blend"
        vOp.vTooltip = "Prefer .blend file downloads"
        vRow.label(text=" Download + Import .blend Files (over FBX)")

        vRow = vCol.row(align=1)
        vRow.separator()
        vOp = vRow.operator(
            "poliigon.poliigon_setting",
            text="",
            depress=cTB.vSettings["download_link_blend"],
            emboss=False,
            icon="CHECKBOX_HLT" if cTB.vSettings["download_link_blend"] else "CHECKBOX_DEHLT",
        )
        vOp.vMode = "download_link_blend"
        vOp.vTooltip = "Link blend files instead of appending"
        vRow.label(text=" Link .blend Files (n/a if any LOD is selected)")
        vRow.enabled = cTB.vSettings["download_prefer_blend"]
        vRow.separator()

        vCol.separator()

        vCol.label(text="Default Model Resolution :")
        vPGrid = vCol.grid_flow(
            row_major=1,
            columns=int((pwidth - 20) / 40),
            even_columns=1,
            even_rows=1,
            align=0,
        )
        for vS in ["1K", "2K", "3K", "4K", "6K", "8K", "16K"]:
            vOp = vPGrid.operator(
                "poliigon.poliigon_setting",
                text=vS,
                depress=(vS in cTB.vSettings["mres"]),
            )
            vOp.vMode = "default_mres_" + vS
            vOp.vTooltip = "The default Texture Resolution to use for Model Assets"

        vCol.separator()
        vCol.separator()

        vRow = vCol.row(align=1)
        vRow.separator()
        vOp = vRow.operator(
            "poliigon.poliigon_setting",
            text="",
            depress=cTB.vSettings["download_lods"],
            emboss=False,
            icon="CHECKBOX_HLT" if cTB.vSettings["download_lods"] else "CHECKBOX_DEHLT",
        )
        vOp.vMode = "download_lods"
        vOp.vTooltip = "Download Model LODs"
        vRow.label(text=" Download Model LODs")
        vRow.separator()

        vCol.separator()

        vLodCol = vCol.column()
        vLodCol.enabled = cTB.vSettings["download_lods"]

        vLodCol.label(text="Default LOD to load (NONE to .blend files, otherwise FBX) :")
        vPGrid = vLodCol.grid_flow(
            row_major=1,
            columns=int((pwidth - 20) / 50),
            even_columns=1,
            even_rows=1,
            align=0,
        )
        lod_list = ["NONE", "SOURCE", "LOD0", "LOD1", "LOD2", "LOD3", "LOD4"]
        for vL in lod_list:
            vOp = vPGrid.operator(
                "poliigon.poliigon_setting",
                text=vL,
                depress=(vL in cTB.vSettings["lod"]),
            )
            vOp.vMode = "default_lod_" + vL
            vOp.vTooltip = "The default LOD to use for Model Assets"

        vCol.separator()

        # .....................................................................

        vCol = vDownloadCol.box().column()

        vCol.separator()

        vCol.label(text="Default HDRI Lighting Resolution :")
        vPGrid = vCol.grid_flow(
            row_major=1,
            columns=int((pwidth - 20) / 40),
            even_columns=1,
            even_rows=1,
            align=0,
        )
        for vS in cTB.HDRI_RESOLUTIONS:
            vOp = vPGrid.operator(
                "poliigon.poliigon_setting",
                text=vS,
                depress=(vS == cTB.vSettings["hdri"]),
            )
            vOp.vMode = "default_hdri_" + vS
            vOp.vTooltip = "The default Resolution to use for HDRI Lighting"

        # .....................................................................

        vCol.separator()

        vRow = vCol.row(align=1)
        vRow.separator()
        vOp = vRow.operator(
            "poliigon.poliigon_setting",
            text="",
            depress=cTB.vSettings["hdri_use_jpg_bg"],
            emboss=False,
            icon="CHECKBOX_HLT" if cTB.vSettings["hdri_use_jpg_bg"] else "CHECKBOX_DEHLT",
        )
        vOp.vMode = "hdri_use_jpg_bg"
        vOp.vTooltip = "Use different resolution .jpg for display in background"
        vRow.label(text=" Use JPG for background")

        # .....................................................................

        vCol.label(text="Default HDRI Background Resolution :")
        vPGrid = vCol.grid_flow(
            row_major=1,
            columns=int((pwidth - 20) / 40),
            even_columns=1,
            even_rows=1,
            align=0,
        )
        vPGrid.enabled = cTB.vSettings["hdri_use_jpg_bg"]

        idx_res_light = cTB.HDRI_RESOLUTIONS.index(cTB.vSettings["hdri"])

        col_no_1k_button = vPGrid.column()
        for vS in cTB.HDRI_RESOLUTIONS[1:]:
            col_button = vPGrid.column()
            col_button.enabled = cTB.HDRI_RESOLUTIONS.index(vS) > idx_res_light
            vOp = col_button.operator(
                "poliigon.poliigon_setting",
                text=vS,
                depress=(vS == cTB.vSettings["hdrib"]),
            )
            vOp.vMode = "default_hdrib_" + vS
            vOp.vTooltip = "The default Resolution to use for HDRI Backgrounds"

        vCol.separator()

        # .....................................................................

        """vCol.label(text="Default HDRI Format :")
        vPGrid = vCol.grid_flow(
            row_major=1,
            columns=int((pwidth - 20) / 40),
            even_columns=1,
            even_rows=1,
            align=0,
        )
        for vF in ["JPG", "EXR"]:
            vOp = vPGrid.operator(
                "poliigon.poliigon_setting",
                text=vF,
                depress=(vF in cTB.vSettings["hdrif"]),
            )
            vOp.vMode = "default_hdrif_" + vF
            vOp.vTooltip = "The default Format in which to download HDRI Assets"

        vCol.separator()"""

        # .....................................................................

        vCol = vDownloadCol.box().column()

        vCol.separator()

        vCol.label(text="Default Brush Resolution :")
        vPGrid = vCol.grid_flow(
            row_major=1,
            columns=int((pwidth - 20) / 40),
            even_columns=1,
            even_rows=1,
            align=0,
        )
        for vS in ["1K", "2K", "3K", "4K"]:
            vOp = vPGrid.operator(
                "poliigon.poliigon_setting",
                text=vS,
                depress=(vS in cTB.vSettings["brush"]),
            )
            vOp.vMode = "default_brush_" + vS
            vOp.vTooltip = "The default Resolution to use for Brushes"

        vCol.separator()

        # .....................................................................

        vCol = vDownloadCol.box().column()

        vCol.separator()

        vCol.label(text="Purchase Preferences :")

        vRow = vCol.row(align=1)
        vRow.separator()
        vOp = vRow.operator(
            "poliigon.poliigon_setting",
            text="",
            depress=cTB.vSettings["auto_download"],
            emboss=False,
            icon="CHECKBOX_HLT" if cTB.vSettings["auto_download"] else "CHECKBOX_DEHLT",
        )
        vOp.vMode = "auto_download"
        vOp.vTooltip = "Auto-Download Assets on Purchase"
        vRow.label(text=" Auto-Download Assets on Purchase")
        vRow.separator()

        vCol.separator()

        # .....................................................................

        vCol = vDownloadCol.box().column()

        vCol.separator()

        vCol.label(text="Import Preferences :")

        vRow = vCol.row(align=1)
        vRow.separator()
        icon = "CHECKBOX_HLT" if self.use_micro_displacements else "CHECKBOX_DEHLT"
        vRow.alignment = "LEFT"
        vRow.prop(self, "use_micro_displacements", icon=icon, emboss=False)
        vRow.separator()

        vRow = vCol.row(align=1)
        vRow.separator()
        vOp = vRow.operator(
            "poliigon.poliigon_setting",
            text="",
            depress=cTB.vSettings["use_16"],
            emboss=False,
            icon="CHECKBOX_HLT" if cTB.vSettings["use_16"] else "CHECKBOX_DEHLT",
        )
        vOp.vMode = "use_16"
        vOp.vTooltip = "Use 16 bit Maps if available"
        vRow.label(text=" Use 16 bit Maps")
        vRow.separator()

    # UPDATER PREFS ...........................................................

    vDownloadCol = self.layout.column(align=1)
    vBox = vDownloadCol.box()

    if self.show_updater_prefs:
        icon = "DISCLOSURE_TRI_DOWN"
    else:
        icon = "DISCLOSURE_TRI_RIGHT"

    if cTB.updater.update_ready:
        text = f"Update available! {cTB.updater.update_data.version}"
    else:
        text = "Addon Updates"

    vBox.prop(self, "show_updater_prefs", emboss=False, icon=icon, text=text)

    if self.show_updater_prefs:
        col = vBox.column()

        colrow = col.row(align=True)
        rsplit = colrow.split(factor=0.5)
        subcol = rsplit.column()
        row = subcol.row(align=True)
        row.scale_y = 1.5

        # If already checked for update, show a refresh button (no label)
        if cTB.updater.update_ready is not None:
            row.operator("poliigon.check_update",
                         text="", icon="FILE_REFRESH")

        subcol = row.column(align=True)
        if cTB.updater.is_checking:
            subcol.operator("poliigon.check_update",
                            text="Checking...")
            subcol.enabled = False
        elif cTB.updater.update_ready is True:
            btn_label = f"Update ready: {cTB.updater.update_data.version}"
            ops = subcol.operator(
                "poliigon.poliigon_link",
                text=btn_label,
            )
            ops.vMode = "notify@{}@{}@{}".format(
                cTB.updater.update_data.url,
                "Install Update",
                "UPDATE_READY_MANUAL_INSTALL_PREFERENCES")
            ops.vTooltip = "Download the new update from website"
        elif cTB.updater.update_ready is False:
            subcol.operator("poliigon.check_update",
                            text="No updates available")
            subcol.enabled = False
        else:
            subcol.operator("poliigon.check_update",
                            text="Check for update")

        # Display user preference option for auto update.
        subcol = rsplit.column()
        subcol.scale_y = 0.8
        subcol.prop(self, "auto_check_update")

        # Next row, show time since last check.
        if cTB.updater.last_check:
            time = cTB.updater.last_check
            last_update = f"Last check: {time}"
        else:
            last_update = "(no recent check for update)"
        subcol.label(text=last_update)

    self.layout.prop(self, "verbose_logs")
    self.layout.prop(self, "reporting_opt_in")
    row = self.layout.row(align=True)
    ops = row.operator(
        "poliigon.poliigon_link",
        text="Terms & Conditions",
    )
    ops.vTooltip = "Open Terms & Conditions"
    ops.vMode = "terms"

    ops = row.operator(
        "poliigon.poliigon_link",
        text="Privacy Policy",
    )
    ops.vTooltip = "Open Privacy Policy"
    ops.vMode = "privacy"

    if cTB.env.env_name and "prod" not in cTB.env.env_name.lower():
        self.layout.alert = True
        msg = f"Active environment: {cTB.env.env_name}, API: {cTB.env.api_url}"
        self.layout.label(text=msg, icon="ERROR")
        self.layout.alert = False


class PoliigonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    scriptdir = bpy.path.abspath(os.path.dirname(__file__))

    reporting_opt_in: bpy.props.BoolProperty(
        name="Share addon errors/usage",
        default=True,
        description=(
            "Automatically share addon activity and any encountered errors "
            "with developers to help improve the product"
        ),
        update=optin_update
    )
    verbose_logs: bpy.props.BoolProperty(
        name="Verbose logging to console",
        default=True,
        description=(
            "Print out more verbose errors to the console, useful for "
            "troubleshooting issues"
        ),
        update=verbose_update
    )
    use_micro_displacements: bpy.props.BoolProperty(
        name="Use micro-displacements (if available, enables experimental)",
        default=False,
        description=(
            "Enable micro-displacements using adaptive subdivision.\n"
            "Note! This will enable Blender's experimental mode if not already active"
        )
    )
    show_updater_prefs: bpy.props.BoolProperty(
        name="Show/hide updater preferences",
        default=True,
        description="Show/hide updater-related preferences"
    )
    auto_check_update: bpy.props.BoolProperty(
        name="Auto-check for update (daily)",
        default=True,
        description=("Check for an addon update once per day,\n"
                     "only runs if the addon is in use.")
    )

    @reporting.handle_draw()
    def draw(self, context):
        f_BuildSettings(self, context)


def register():
    bpy.utils.register_class(PoliigonPreferences)
    optin_update(None, bpy.context)


def unregister():
    bpy.utils.unregister_class(PoliigonPreferences)
