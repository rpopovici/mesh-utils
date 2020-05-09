bl_info = {
    "name": "Select Interior Faces",
    "author": "rpopovici",
    "version": (0, 5),
    "blender": (2, 80, 0),
    "location": "(Edit Mode) Select > Select All by Trait",
    "description": "Select interior faces. This solution is based on AO map baking",
    "warning": "",
    "wiki_url": "https://github.com/rpopovici/mesh-utils",
    "category": "Mesh",
    }

import bpy
import bmesh
from mathutils import Vector

def hit_test(pixels, resolution, xpos, ypos):
    count = 0
    for i in range(-1, 2):
        for j in range(-1, 2):
            red = pixels[4 * (xpos + i + resolution * (ypos + j)) + 0]
            alpha = pixels[4 * (xpos + i + resolution * (ypos + j)) + 3]
            if (red == 0) and (alpha != 0):
                count += 1
    return count > 0

# clean-up light leaks
def clean_up(pixels, resolution):
    for xpos in range(1, resolution - 1):
        for ypos in range(1, resolution - 1):
            red = pixels[4 * (xpos + resolution * ypos) + 0]
            alpha = pixels[4 * (xpos + resolution * ypos) + 3]
            if (red != 0) and (alpha != 0):
                count = 0
                for i in range(-1, 2):
                    for j in range(-1, 2):
                        r = pixels[4 * (xpos + i + resolution * (ypos + j)) + 0]
                        a = pixels[4 * (xpos + i + resolution * (ypos + j)) + 3]
                        if (r != 0) and (a != 0):
                            count += 1
                if (count > 0) and (count < 3):
                    # remove pixel
                    pixels[4 * (xpos + resolution * ypos) + 0] = 0.0


def hit_test_area(pixels, resolution, xpos_min, ypos_min, xpos_max, ypos_max):
    tolerance = 1
    count = 0
    for i in range(xpos_min, xpos_max + 1):
        for j in range(ypos_min, ypos_max + 1):
            red = pixels[4 * (i + resolution * j) + 0]
            alpha = pixels[4 * (i + resolution * j) + 3]
            if (red != 0) and (alpha != 0):
                count += 1
    return count < tolerance


def select_interior_faces(context, obj, bake_type, resolution, samples, bounces):
    ao_map_size = resolution
    selected_objects = bpy.context.selected_objects
    context.scene.render.engine = 'CYCLES'
    context.scene.cycles.samples = samples
    #bpy.context.scene.render.layers["RenderLayer"].cycles.use_denoising = True

    ##sampling;=path tracing 
    bpy.context.scene.cycles.progressive = 'PATH'
    #bpy.context.scene.cycles.samples = 50
    bpy.context.scene.cycles.max_bounces = bounces
    bpy.context.scene.cycles.min_bounces = bounces
    bpy.context.scene.cycles.diffuse_bounces = bounces
    bpy.context.scene.cycles.glossy_bounces = 0
    bpy.context.scene.cycles.transmission_bounces = 0
    bpy.context.scene.cycles.volume_bounces = 0
    bpy.context.scene.cycles.transparent_max_bounces = 0
    bpy.context.scene.cycles.transparent_min_bounces = 0
    #bpy.context.scene.cycles.use_progressive_refine = True

    context.scene.cycles.sample_clamp_indirect = 0.0

    context.scene.cycles.blur_glossy = 0.0
    bpy.context.scene.cycles.caustics_reflective = False
    bpy.context.scene.cycles.caustics_refractive = False

    # bpy.context.scene.render.tile_x = 64
    # bpy.context.scene.render.tile_y = 64

    # context.scene.render.use_simplify = True
    # bpy.context.scene.cycles.ao_bounces_render = 64
    
    # world light
    world = bpy.data.worlds['World']
    world.use_nodes = True

    # changing these values does affect the render.
    bg = world.node_tree.nodes['Background']
    bg.inputs[0].default_value[:3] = (1.0, 1.0, 1.0)
    bg.inputs[1].default_value = 1.0

    world.cycles_visibility.camera = False
    world.cycles_visibility.glossy = False
    world.cycles_visibility.transmission = False
    world.cycles_visibility.scatter = False

    world.cycles.sampling_method = 'MANUAL'
    world.cycles.sample_map_resolution = 1024
    #world.cycles.max_bounces = 2048
    #world.cycles.volume_sampling = "MULTIPLE_IMPORTANCE"

    # add new UV layer
    uv_layer =  obj.data.uv_layers.get("__AO_UV_LAYER__")
    if not uv_layer:
        uv_layer = obj.data.uv_layers.new(name="__AO_UV_LAYER__")
    uv_layer.active = True

    # quick face unwrap
    #bpy.ops.mesh.select_all(action='SELECT')
    #bpy.ops.uv.smart_project(angle_limit=1.0, island_margin=0.01, user_area_weight=0.0, use_aspect=True, stretch_to_bounds=True)
    bpy.ops.uv.lightmap_pack(PREF_CONTEXT='ALL_FACES', PREF_PACK_IN_ONE=True, PREF_NEW_UVLAYER=False, PREF_APPLY_IMAGE=False, PREF_IMG_PX_SIZE=ao_map_size, PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.2)
    bpy.ops.mesh.select_all(action='DESELECT')

    # creating a new material and add a new image texture node to it
    bake_material = bpy.data.materials.new('__AO_BAKE_MAT__')
    bake_material.use_nodes = True
    #bake_material.diffuse_color = (1, 1, 1, 1)
    #bake_material.roughness = 0
    #bake_material.specular_color = (1, 1, 1)
    #bake_material.metallic = 1

    #bpy.data.node_groups["Shader NodeTree"].nodes["Principled BSDF"].inputs[0].default_value = (0, 1, 0, 1)
    bake_material.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (1, 1, 1, 1)
    bake_material.node_tree.nodes["Principled BSDF"].inputs[4].default_value = 0
    bake_material.node_tree.nodes["Principled BSDF"].inputs[5].default_value = 1
    bake_material.node_tree.nodes["Principled BSDF"].inputs[7].default_value = 0

    image_texture_node = bake_material.node_tree.nodes.new('ShaderNodeTexImage')
    image_texture_node.select = True
    #bake_material.node_tree.nodes.active = image_texture_node

    # add emission node
    # material_output = bake_material.node_tree.nodes["Principled BSDF"] #bake_material.node_tree.nodes.get('Material Output')
    # emission = bake_material.node_tree.nodes.new('ShaderNodeEmission')
    # emission.inputs['Strength'].default_value = 5.0
    # # link emission shader to material
    # bake_material.node_tree.links.new(material_output.inputs[0], emission.outputs[0])

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

    # ['COMBINED', 'AO', 'SHADOW', 'NORMAL', 'UV', 'ROUGHNESS', 'EMIT', 'ENVIRONMENT', 'DIFFUSE', 'GLOSSY', 'TRANSMISSION', 'SUBSURFACE']
    # pass_filter = {'NONE', 'AO', 'EMIT', 'DIRECT', 'INDIRECT', 'COLOR', 'DIFFUSE', 'GLOSSY', 'TRANSMISSION', 'SUBSURFACE'}
    bpy.ops.object.bake(type = bake_type,  width = resolution, height = resolution, margin = 0) #, uv_layer = uv_layer.name)

    # select "black" faces from AO
    me = obj.data
    bm = bmesh.from_edit_mesh(me)

    #uv_layer = bm.loops.layers.uv.verify()
    #bm.faces.layers.tex.verify()
    uv_layer = bm.loops.layers.uv.get("__AO_UV_LAYER__")

    # down scale Uvs
    # for f in bm.faces:
    #     for l in f.loops:
    #         l[uv_layer].uv *= 0.99
    #         l[uv_layer].uv += Vector((0.005, 0.005))

    # Extract pixels to new array for performance gain
    pixels_copy = list(ao_map.pixels[:])
    clean_up(pixels_copy, resolution)

    # determine bbox
    xpos_min = float("inf")
    xpos_max = float("-inf")
    ypos_min = float("inf")
    ypos_max = float("-inf")
    for face in bm.faces:
        if face.hide:
            continue
        face_select = True
        for loop in face.loops:
            luv = loop[uv_layer]
            uv = luv.uv
            xpos = round(uv.x * (resolution - 1))
            ypos = round(uv.y * (resolution - 1))
            if xpos_min > xpos:
                xpos_min = xpos
            if xpos_max < xpos:
                xpos_max = xpos
            if ypos_min > ypos:
                ypos_min = ypos
            if ypos_max < ypos:
                ypos_max = ypos
            # select face if RED color channel is black
            #if ao_map.pixels[4 * (xpos + resolution * ypos) + 0] != 0:
            #if not hit_test(pixels_copy, resolution, xpos, ypos):
            #    face_select = False
        if not hit_test_area(pixels_copy, resolution, xpos_min, ypos_min, xpos_max, ypos_max):
            face_select = False
        face.select_set(face_select)

        xpos_min = float("inf")
        xpos_max = float("-inf")
        ypos_min = float("inf")
        ypos_max = float("-inf")


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

    bake_type: bpy.props.EnumProperty(
        items=[
                ('AO', "AO", "Bake AO map for occlusion detection"),
                ('DIFFUSE', "DIFFUSE", "Bake Diffuse map for occlusion detection. Lights are required to properly illuminate hidden areas you wish to keep"),
                ],
        name="Bake Mode",
        default="AO",
        description="",
        )

    resolution: bpy.props.EnumProperty(
        items=[
                ('512', "512", ""),
                ('1024', "1024", ""),
                ('2048', "2048", ""),
                ('4096', "4096", ""),
                ],
        name="Resolution",
        default="1024",
        description="",
        )

    samples: bpy.props.IntProperty(
        name = "Samples",
        default = 64,
        min = 1,
        max = 1024,
        description = "Cycles rendering samples per pixel",
        )

    bounces: bpy.props.IntProperty(
        name = "Bounces",
        default = 128,
        min = 1,
        max = 1024,
        description = "Cycles rendering light bounces",
        )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        select_interior_faces(context, obj, self.bake_type, int(self.resolution), self.samples, self.bounces)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.execute(context)
        return {"FINISHED"}

def menu_func(self, context):
    self.layout.operator(SelectInteriorFaces.bl_idname, text="Interior Faces (Cycles Bake)")

def register():
    # bpy.utils.register_class(SelectInteriorFaces)

    # Add "Extras" menu to the "Add Mesh" menu
    bpy.types.VIEW3D_MT_edit_mesh_select_by_trait.append(menu_func)

def unregister():
    # bpy.utils.unregister_class(SelectInteriorFaces)

    # Remove "Extras" menu from the "Add Mesh" menu.
    bpy.types.VIEW3D_MT_edit_mesh_select_by_trait.remove(menu_func)

# if __name__ == "__main__":
#     register()
