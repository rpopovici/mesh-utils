bl_info = {
    "name": "Mesh from UVs",
    "author": "rpopovici",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "(Object Mode) Add > Mesh > Mesh from UVs",
    "description": "Create mesh from UVs",
    "warning": "",
    "wiki_url": "https://github.com/rpopovici/mesh-utils",
    "category": "Mesh",
    }

import bpy
from mathutils import Vector

def create_object_from_data(context, name, verts, faces):
    # Create new mesh & object
    mesh = bpy.data.meshes.new(name + 'Mesh')
    obj = bpy.data.objects.new(name, mesh)
    obj.show_name = True

    # Link the newly created object to the scene and make it active
    context.view_layer.active_layer_collection.collection.objects.link(obj)
    context.view_layer.objects.active = obj
    obj.select_set(True)

    # populate mesh with data from given verts & faces
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return obj

def generate_mesh_data_from_uv(context, obj, size, interpolate):
    out_verts = []
    out_faces = []
    for face in obj.data.polygons:
        out_face = []
        for vert, loop in zip(face.vertices, face.loop_indices):
            coord = obj.data.vertices[vert].co
            uv = obj.data.uv_layers.active.data[loop].uv
            uv_vert = ((uv.x - 0.5) * size, 0, (uv.y - 0.5) * size)
            out_verts.append(coord.lerp(uv_vert, interpolate))
            out_face.append(loop)
        out_faces.append(out_face)

    return (out_verts, out_faces)

class MeshFromUV(bpy.types.Operator):
    """Mesh from UVs"""
    bl_idname = 'mesh.mesh_from_uv'
    bl_label = 'Mesh From UVs'
    bl_options = {'REGISTER', 'UNDO'}

    size: bpy.props.FloatProperty(
        name = "Size",
        subtype ='DISTANCE',
        default = 10.0,
        min = 0.1,
        max = 100.0,
        description = "Object size",
        unit ='LENGTH',
        )

    interpolate: bpy.props.FloatProperty(
        name = "Interpolate",
        default = 1.0,
        min = 0.0,
        max = 1.0,
        description = "Interpolate between 3D coords and UV coords",
        )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        self.mesh_from_uv(context)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.execute(context)
        return {"FINISHED"}

    def mesh_from_uv(self, context):
        obj = context.active_object
        (out_verts, out_faces) = generate_mesh_data_from_uv(context, obj, self.size, self.interpolate)
        create_object_from_data(context, obj.name + '_UVMesh', out_verts, out_faces)

def menu_func(self, context):
    self.layout.operator(MeshFromUV.bl_idname, text="Mesh From UVs")

def register():
    # bpy.utils.register_class(MeshFromUV)

    # Add "Extras" menu to the "Add Mesh" menu
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)

def unregister():
    # bpy.utils.unregister_class(MeshFromUV)

    # Remove "Extras" menu from the "Add Mesh" menu.
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)

# if __name__ == "__main__":
#     register()
