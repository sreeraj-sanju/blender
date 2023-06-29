import bpy


class HelloWorldPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Hello World Panel"
    bl_idname = "PT_sreeraj_test"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MY FIRST"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.label(text="Hello world!", icon='WORLD_DATA')



def register():
    bpy.utils.register_class(HelloWorldPanel)


def unregister():
    bpy.utils.unregister_class(HelloWorldPanel)


if __name__ == "__main__":
    register()
