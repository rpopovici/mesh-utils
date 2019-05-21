bl_info = {
    "name": "Select All by Trait",
    "author": "rpopovici",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "(Edit Mode) Select > Select All by Trait",
    "description": "Select Bevel/Crease/Seam/Sharp/Freestyle by Trait",
    "warning": "",
    "wiki_url": "https://github.com/rpopovici/blender-addons",
    "category": "Mesh",
    }

import bpy
import bmesh

def select_bevel_edges(context, obj):
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)

    if hasattr(bm.edges, "ensure_lookup_table"):
        bm.edges.ensure_lookup_table()

    bw = bm.edges.layers.bevel_weight.verify()
    for edge in bm.edges:
        if edge[bw] != 0:
            edge.select_set(True)

    # Show the updates in the viewport
    bm.select_flush_mode()
    bmesh.update_edit_mesh(mesh, False)

def select_crease_edges(context, obj):
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)

    if hasattr(bm.edges, "ensure_lookup_table"):
        bm.edges.ensure_lookup_table()

    cs = bm.edges.layers.crease.verify()
    for edge in bm.edges:
        if edge[cs] != 0:
            edge.select_set(True)

    # Show the updates in the viewport
    bm.select_flush_mode()
    bmesh.update_edit_mesh(mesh, False)

# seam
def select_seam_edges(context, obj):
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)

    if hasattr(bm.edges, "ensure_lookup_table"):
        bm.edges.ensure_lookup_table()

    for edge in bm.edges:
        if edge.seam:
            edge.select_set(True)

    # Show the updates in the viewport
    bm.select_flush_mode()
    bmesh.update_edit_mesh(mesh, False)

# smooth
def select_sharp_edges(context, obj):
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)

    if hasattr(bm.edges, "ensure_lookup_table"):
        bm.edges.ensure_lookup_table()

    for edge in bm.edges:
        if not edge.smooth:
            edge.select_set(True)

    # Show the updates in the viewport
    bm.select_flush_mode()
    bmesh.update_edit_mesh(mesh, False)

def select_freestyle_edges(context, obj):
    mesh = obj.data

    bm = bmesh.from_edit_mesh(mesh)

    if hasattr(bm.edges, "ensure_lookup_table"):
        bm.edges.ensure_lookup_table()

    fs = bm.edges.layers.freestyle.verify()
    for edge in bm.edges:
        print(edge[fs])
        if mesh.edges[edge.index].use_freestyle_mark:
            edge.select_set(True)

    # Show the updates in the viewport
    bm.select_flush_mode()
    bmesh.update_edit_mesh(mesh, False)

class SelectAllByTrait(bpy.types.Operator):
    """Select All by Trait"""
    bl_idname = 'mesh.select_all_by_trait'
    bl_label = 'Select All by Trait'
    bl_options = {'REGISTER', 'UNDO'}

    select_type: bpy.props.EnumProperty(
        items=[
                ('BEVEL', "Bevel", "Select beveled edges"),
                ('CREASE', "Crease", "Select creased edges"),
                ('SEAM', "Seam", "Select seam edges"),
                ('SHARP', "Sharp", "Select sharp edges"),
                ('FREESTYLE', "Freestyle", "Select freestyle edges"),
                ],
        name="Selection Type",
        description="",
        )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        self.select_all_by_trait(context)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.execute(context)
        return {"FINISHED"}

    def select_all_by_trait(self, context):
        # force context update in edit mode
        # apparently there's a bug in scene.update()
        #bpy.context.scene.update()
        mode = bpy.context.object.mode
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
            bpy.ops.object.mode_set(mode = mode)

        obj = context.active_object

        if self.select_type == 'BEVEL':
            select_bevel_edges(context, obj)
        elif self.select_type == 'CREASE':
            select_crease_edges(context, obj)
        elif self.select_type == 'SEAM':
            select_seam_edges(context, obj)
        elif self.select_type == 'SHARP':
            select_sharp_edges(context, obj)
        elif self.select_type == 'FREESTYLE':
            select_freestyle_edges(context, obj)

def menu_func(self, context):
    self.layout.separator()
    self.layout.operator(SelectAllByTrait.bl_idname, text="Bevel").select_type = 'BEVEL'
    self.layout.operator(SelectAllByTrait.bl_idname, text="Crease").select_type = 'CREASE'
    self.layout.operator(SelectAllByTrait.bl_idname, text="Seam").select_type = 'SEAM'
    self.layout.operator(SelectAllByTrait.bl_idname, text="Sharp").select_type = 'SHARP'
    self.layout.operator(SelectAllByTrait.bl_idname, text="Freestyle").select_type = 'FREESTYLE'

def register():
    bpy.utils.register_class(SelectAllByTrait)

    bpy.types.VIEW3D_MT_edit_mesh_select_by_trait.append(menu_func)

def unregister():
    bpy.utils.unregister_class(SelectAllByTrait)

    bpy.types.VIEW3D_MT_edit_mesh_select_by_trait.remove(menu_func)

if __name__ == "__main__":
    register()
