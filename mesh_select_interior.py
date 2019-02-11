bl_info = {
    "name": "Select Interior Faces",
    "author": "rpopovici",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "(Edit Mode) Select > Select All by Trait",
    "description": "Select interior faces. This solution is based on AO map baking",
    "warning": "",
    "wiki_url": "https://github.com/rpopovici/blender-addons",
    "category": "Mesh",
    }

import bpy
import bmesh

def select_interior_faces(context, obj, resolution):
    ao_map_size = resolution
    selected_objects = bpy.context.selected_objects
    context.scene.render.engine = 'CYCLES'
    #bpy.context.scene.render.layers["RenderLayer"].cycles.use_denoising = True

    # add new UV layer
    uv_layer =  obj.data.uv_layers.get("__AO_UV_LAYER__")
    if not uv_layer:
        uv_layer = obj.data.uv_layers.new(name="__AO_UV_LAYER__")
    uv_layer.active = True

    # quick face unwrap
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.05, user_area_weight=0.0, use_aspect=True, stretch_to_bounds=True)
    bpy.ops.mesh.select_all(action='DESELECT')

    # creating a new material and add a new image texture node to it
    bake_material = bpy.data.materials.new('__AO_BAKE_MAT__')
    bake_material.use_nodes = True
    image_texture_node = bake_material.node_tree.nodes.new('ShaderNodeTexImage')
    image_texture_node.select = True
    #bake_material.node_tree.nodes.active = image_texture_node

    old_mat = None
    # Assign material to object
    if obj.data.materials:
        # assign to 1st material slot
        old_mat = obj.data.materials[0]
        obj.data.materials[0] = bake_material
    else:
        # no slots
        obj.data.materials.append(bake_material)

    obj.active_material_index = 0

    # activating the object
    #bpy.context.scene.objects.active = obj
    bpy.context.view_layer.objects.active = obj

    # create a new image and assign it to the image texture node
    ao_map = bpy.data.images.new(name=(obj.name + "_AO"), width = ao_map_size, height = ao_map_size)
    image_texture_node.image = ao_map

    # hide from rendering
    # for obj in bpy.data.objects:
    #     if obj.hide_viewport:
    #         obj.hide_render = True

    # start baking
    bpy.ops.object.bake(type = 'AO', width = resolution, height = resolution) #, uv_layer = uv_layer.name)

    # select "black" faces from AO
    me = obj.data
    bm = bmesh.from_edit_mesh(me)

    #uv_layer = bm.loops.layers.uv.verify()
    #bm.faces.layers.tex.verify()
    uv_layer = bm.loops.layers.uv.get("__AO_UV_LAYER__")

    for face in bm.faces:
        face_select = True
        for loop in face.loops:
            luv = loop[uv_layer]
            uv = luv.uv
            xpos = round(uv.x * resolution)
            ypos = round(uv.y * resolution)
            # select face if RED color channel is black
            if ao_map.pixels[4 * (xpos + resolution * ypos) + 0] != 0: 
                face_select = False
        face.select = face_select

    bmesh.update_edit_mesh(me)

    # clean up
    bpy.data.images.remove(ao_map)
    uv_layer = obj.data.uv_layers.get("__AO_UV_LAYER__")
    obj.data.uv_layers.remove(uv_layer)
    
    if not old_mat:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.material_slot_remove()
        bpy.ops.object.mode_set(mode='EDIT')
    else:
        obj.data.materials[0] = old_mat

    bpy.data.materials.remove(bake_material)


class SelectInteriorFaces(bpy.types.Operator):
    """Select Interior Faces"""
    bl_idname = 'mesh.select_interior_faces'
    bl_label = 'Select interior faces'
    bl_options = {'REGISTER', 'UNDO'}

    resolution: bpy.props.IntProperty(
        name = "Resolution",
        default = 512,
        min = 512,
        max = 4096,
        description = "AO bake image size",
        )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        select_interior_faces(context, obj, self.resolution)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.execute(context)
        return {"FINISHED"}

def menu_func(self, context):
    self.layout.operator(SelectInteriorFaces.bl_idname, text="Interior Faces (AO Bake)")

def register():
    bpy.utils.register_class(SelectInteriorFaces)

    # Add "Extras" menu to the "Add Mesh" menu
    bpy.types.VIEW3D_MT_edit_mesh_select_by_trait.append(menu_func)

def unregister():
    bpy.utils.unregister_class(SelectInteriorFaces)

    # Remove "Extras" menu from the "Add Mesh" menu.
    bpy.types.VIEW3D_MT_edit_mesh_select_by_trait.remove(menu_func)

if __name__ == "__main__":
    register()
