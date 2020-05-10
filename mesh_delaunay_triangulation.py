bl_info = {
    "name": "Delaunay triangulation",
    "author": "rpopovici",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "(Object Mode) Add > Mesh > Delaunay triangulation",
    "description": "Delaunay triangulation",
    "warning": "",
    "wiki_url": "https://github.com/rpopovici/mesh-utils",
    "category": "Mesh",
    }

import bpy
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

def create_object_from_data(context, name, verts, edges, faces):
    # Create new mesh & object
    mesh = bpy.data.meshes.new(name + '_TRIS')
    obj = bpy.data.objects.new(name, mesh)
    obj.show_name = True

    # Link the newly created object to the scene and make it active
    context.view_layer.active_layer_collection.collection.objects.link(obj)
    context.view_layer.objects.active = obj
    obj.select_set(True)

    # populate mesh with data from given verts & faces
    mesh.from_pydata(verts, edges, faces)
    mesh.update()

    # wireframe display
    obj.show_wire = True

    return obj

def delaunay_triangulate(context, obj, output_type, epsilon):
    depsgraph = context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    mesh_eval = obj_eval.to_mesh()

    vert_coords = [vtx.co.to_2d() for vtx in mesh_eval.vertices]
    edges = [edge.vertices for edge in mesh_eval.edges]
    faces = [[mesh_eval.loops[loop_index].vertex_index for loop_index in face.loop_indices] for face in mesh_eval.polygons]

    (out_coords, out_edges, out_faces, orig_verts, orig_edges, orig_faces) = delaunay_2d_cdt(vert_coords, edges, faces, output_type, epsilon)

    obj_eval.to_mesh_clear()
    #bpy.data.meshes.remove(mesh_eval)

    return ([co.to_3d() for co in out_coords], out_edges, out_faces)

class DelaunayTriangulation(bpy.types.Operator):
    """Delaunay Triangulation"""
    bl_idname = 'mesh.delaunay_triangulation'
    bl_label = 'Delaunay Triangulation'
    bl_options = {'REGISTER', 'UNDO'}

    output_type: bpy.props.EnumProperty(
        items = [
                ('0', "CONVEX HULL", "Triangles with convex hull"),
                ('1', "CONSTRAINTS INSIDE", "Triangles inside constraints"),
                ('2', "CONSTRAINTS INTERSECT", "The input constraints, intersected"),
                ('3', "CONSTRAINTS INTERSECT BMESH", " Like 2 but with extra edges to make valid BMesh faces"),
                ],
        name = "Output Type",
        default = "1",
        description = "",
        )

    epsilon: bpy.props.FloatProperty(
        name = "Epsilon",
        subtype ='DISTANCE',
        default = 0.0001,
        min = 0.000001,
        max = 1.0,
        description = "Epsilon",
        unit ='LENGTH',
        )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        self.triangulate_mesh(context)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.execute(context)
        return {"FINISHED"}

    def triangulate_mesh(self, context):
        obj = context.active_object
        (out_verts, out_edges, out_faces) = delaunay_triangulate(context, obj, int(self.output_type), self.epsilon)
        create_object_from_data(context, obj.name + '_TRIS', out_verts, out_edges, out_faces)

        # Hide the object in the viewport
        obj.hide_set(True)

def menu_func(self, context):
    self.layout.operator(DelaunayTriangulation.bl_idname, text="Delaunay Triangulation")

def register():
    # bpy.utils.register_class(DelaunayTriangulation)

    # Add "Extras" menu to the "Add Mesh" menu
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)

def unregister():
    # bpy.utils.unregister_class(DelaunayTriangulation)

    # Remove "Extras" menu from the "Add Mesh" menu.
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)

# if __name__ == "__main__":
#     register()
