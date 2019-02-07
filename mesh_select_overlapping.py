bl_info = {
    "name": "Select Overlapping Mesh",
    "author": "rpopovici",
    "version": (0, 3),
    "blender": (2, 80, 0),
    "location": "(Edit Mode) Select > Select All by Trait",
    "description": "Select overlapping vertices/edges/faces",
    "warning": "",
    "wiki_url": "https://github.com/rpopovici/blender-addons",
    "category": "Mesh",
    }

import bpy
import bmesh
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils import Matrix
from mathutils import Vector
from math import radians, sqrt

def measure (first, second):
	locx = second[0] - first[0]
	locy = second[1] - first[1]
	locz = second[2] - first[2]

	distance = sqrt((locx)**2 + (locy)**2 + (locz)**2) 
	return distance

def collinear(vec1, vec2, epsilon):
    return ((vec1.angle(vec2) < epsilon) or (abs(radians(180) - vec1.angle(vec2)) < epsilon))

def adjacent(face, another_face):
    adjacent_faces = []
    for vert in another_face.verts:
        adjacent_faces.extend([f.index for f in vert.link_faces])
    return (face.index in adjacent_faces)

def build_kdtree_from_verts(verts):
    # Create a kd-tree from verts
    size = len(verts)
    kd = KDTree(size)
    for i, vtx in enumerate(verts):
        # exclude hidden geometry
        if not vtx.hide:
            kd.insert(vtx.co, i)
    kd.balance()
    return kd

def build_kdtree_from_coords(coords):
    # Create a kd-tree from coords
    size = len(coords)
    kd = KDTree(size)
    for i, co in enumerate(coords):
        kd.insert(co, i)
    kd.balance()
    return kd

def calc_edge_median(edge):
    return (edge.verts[0].co + edge.verts[1].co) / 2

def find_duplicate_vertices(bm, distance):
    verts = bm.verts
    kd = build_kdtree_from_verts(verts)

    # Select duplicate vertices
    vtx_selection = set()
    for vtx in verts:
        vtx_group = kd.find_range(vtx.co, distance)
        if len(vtx_group) > 1:
            for (co, index, dist) in vtx_group:
                vtx_selection.add(index)
    
    return list(vtx_selection)

def find_self_intersect_faces(bm, distance):
    bhv_tree = BVHTree.FromBMesh(bm, epsilon = 0.0)
    overlap_pairs = bhv_tree.overlap(bhv_tree)
    return overlap_pairs

def find_intersect_faces(bm, bm2, distance):
    bhv_tree = BVHTree.FromBMesh(bm, epsilon = 0.0)
    bhv_tree2 = BVHTree.FromBMesh(bm2, epsilon = 0.0)
    overlap_pairs = bhv_tree.overlap(bhv_tree2)
    return overlap_pairs

def select_duplicate_vertices(context, distance):
    obj = context.active_object
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)
    verts = bm.verts

    if hasattr(bm.verts, "ensure_lookup_table"):
        verts.ensure_lookup_table()

    # Create a kd-tree from a mesh
    kd = build_kdtree_from_verts(verts)

    # Select duplicate vertices
    for i, vtx in enumerate(verts):
        vtx_group = []
        for (co, index, dist) in kd.find_range(vtx.co, distance):
            vtx_group.append(index)
        if len(vtx_group) > 1:
            #print(vtx_group)
            for index in vtx_group:
                if not verts[index].hide:
                    verts[index].select_set(True)

    # Show the updates in the viewport
    bm.select_flush_mode()
    bmesh.update_edit_mesh(mesh, False)


def select_duplicate_edges(context, distance):
    obj = context.active_object
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)
    
    if hasattr(bm.verts, "ensure_lookup_table"):
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

    # find duplicate vertices first
    vtx_group = find_duplicate_vertices(bm, distance)
    
    if len(vtx_group) == 0:
        return

    # get potential duplicate edges
    edges_from_verts = set()
    for vtx_index in vtx_group:
        for edge in bm.verts[vtx_index].link_edges:
            edges_from_verts.add(edge.index)

    # calculate edge center
    edge_centers = [(edge_index, calc_edge_median(bm.edges[edge_index])) for edge_index in edges_from_verts if not bm.edges[edge_index].hide]

    if len(edge_centers) == 0:
        return

    # build KDTree for edge median points
    kd = build_kdtree_from_coords([edge_center[1] for edge_center in edge_centers])
    for (edge_index, edge_center) in edge_centers:
        coord_group = kd.find_range(edge_center, distance)
        if len(coord_group) > 1:
            if not bm.edges[edge_index].hide:
                bm.edges[edge_index].select_set(True)

    bm.select_flush_mode()
    bmesh.update_edit_mesh(mesh, False, False)

def select_intersect_faces(context, intersections, coplanar, inset, tolerance, angle):
    obj = context.active_object
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)

    if hasattr(bm.verts, "ensure_lookup_table"):
        bm.faces.ensure_lookup_table()

    # clone from geometry
    bm_clone = bmesh.new()
    bm_clone.from_mesh(mesh)

    # select all faces
    for face in bm_clone.faces:
        face.select_set(True)

    # split edges
    bmesh.ops.split_edges(bm_clone, edges = bm_clone.edges, verts = [], use_verts=False)

    # calculate avg edge length
    thick_avg = 0.0
    for face in bm_clone.faces:
        perimeter = face.calc_perimeter()
        thick = perimeter / len(face.verts)
        thick_avg += thick

    # inset thickness as factor of distance param
    thick_avg = thick_avg / len(bm_clone.faces) * inset
    #print(thick_avg)

    # clamp on edge length
    min_edge_len = 1000000.0
    for edge in bm_clone.edges:
        edge_length = edge.calc_length()
        if edge_length < min_edge_len:
            min_edge_len = edge_length

    # clamp by smallest edge length
    edge_clamp_limit = min_edge_len * 0.33
    if thick_avg > edge_clamp_limit:
        thick_avg = edge_clamp_limit

    # inset faces by very small amount
    #inset_faces = bmesh.ops.inset_individual(bm_clone, faces=bm_clone.faces, thickness=thick_avg, depth=0.0, use_even_offset=False, use_interpolate=True, use_relative_offset=False)
    bmesh.ops.inset_region(bm_clone, faces=bm_clone.faces, faces_exclude=[], use_boundary=True, use_even_offset=True, use_interpolate=True, use_relative_offset=False, use_edge_rail=False, thickness=thick_avg, depth=0.0, use_outset=False)
    faces_not_select = [face for face in bm_clone.faces if not face.select]
    bmesh.ops.delete(bm_clone, geom=faces_not_select, context='FACES')
    bmesh.ops.recalc_face_normals(bm_clone, faces=bm_clone.faces)

    if (intersections):
        #intersect_pairs = find_intersect_faces(bm, bm_clone, distance)
        intersect_pairs = find_self_intersect_faces(bm_clone, tolerance)

        for pair in intersect_pairs:
            (first_index, second_index) = pair
            # exclude pairs with same index because these are false positive as result of cloning
            if first_index != second_index:
                bm.faces[first_index].select_set(True)
                bm.faces[second_index].select_set(True)

    # coplanar intersections
    if (coplanar):
        bvh_tree = BVHTree.FromBMesh(bm, epsilon = 0.0)
        for face in bm_clone.faces:
            # skip if already selected
            if bm.faces[face.index].select:
                continue
            for vert in face.verts:
                nearest_list = bvh_tree.find_nearest_range(vert.co, tolerance)
                for (location, normal, index, dist) in nearest_list:
                    org_face = bm.faces[face.index]
                    co_face = bm.faces[index]
                    if (index is not None) and (index != face.index) and collinear(org_face.normal, co_face.normal, angle): #(measure(vert.co, location) < 0.0001):
                        #print(co_face.index, location, index, dist)
                        if bmesh.geometry.intersect_face_point(bm.faces[index], vert.co) and (not adjacent(org_face, co_face)):
                            org_face.select_set(True)
                            co_face.select_set(True)

    bm.select_flush_mode()
    bmesh.update_edit_mesh(mesh, False, False)

    #bpy.ops.object.mode_set(mode='OBJECT')
    #bm_clone_resampled.to_mesh(mesh)

    bm_clone.free()

def select_duplicate_faces(context, distance):
    obj = context.active_object
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)
    if hasattr(bm.verts, "ensure_lookup_table"):
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

    vtx_group = find_duplicate_vertices(bm, distance)
    
    if len(vtx_group) == 0:
        return

    faces_from_verts = set()
    for vtx_index in vtx_group:
        for face in bm.verts[vtx_index].link_faces:
            faces_from_verts.add(face.index)
        
    #print(faces_from_verts)
    face_centers = [(face_index, bm.faces[face_index].calc_center_median_weighted()) for face_index in faces_from_verts if not bm.faces[face_index].hide]

    if len(face_centers) == 0:
        return

    kd = build_kdtree_from_coords([face_center[1] for face_center in face_centers])
    for (face_index, face_center) in face_centers:
        coord_group = kd.find_range(face_center, distance)
        if len(coord_group) > 1:
            if not bm.faces[face_index].hide:
                bm.faces[face_index].select_set(True)

    bm.select_flush_mode()
    bmesh.update_edit_mesh(mesh, False, False)
    return

def get_mesh_select_mode():
    (vertex_mode, edge_mode, face_mode) = bpy.context.tool_settings.mesh_select_mode
    if vertex_mode:
        return 'VERT'
    elif edge_mode:
        return 'EDGE'
    elif face_mode:
        return 'FACE'
    else:
        return 'VERT'

class SelectOverlapping(bpy.types.Operator):
    """Select overlapping mesh"""
    bl_idname = 'mesh.select_overlapping'
    bl_label = 'Select Overlapping'
    bl_options = {'REGISTER', 'UNDO'}

    select_type: bpy.props.EnumProperty(
        items=[
                ('VERT', "Vertices", "Select overlapping vertices"),
                ('EDGE', "Edges", "Select overlapping edges"),
                ('FACE', "Faces", "Select overlapping faces"),
                ],
        name="Selection Mode",
        description="",
        )

    overlapping: bpy.props.BoolProperty(
        name="Overlapping",
        description="Select overlapping mesh",
        default = True
        )

    distance: bpy.props.FloatProperty(
        name = "Distance",
        subtype ='DISTANCE',
        default = 0.0001,
        min = 0.0,
        max = 100.0,
        description = "Minimum overlapping distance between vertices to select",
        unit ='LENGTH',
        )

    intersections: bpy.props.BoolProperty(
        name="Intersections",
        description="Select intersecting faces",
        default = False
        )

    inset: bpy.props.FloatProperty(
        name = "Inset",
        subtype='DISTANCE',
        default = 0.0001,
        min = 0.0,
        max = 1.0,
        description = "Inset factor between adjacent faces",
        unit='LENGTH'
        )

    coplanar: bpy.props.BoolProperty(
        name="Coplanar",
        description="Select coplanar faces",
        default = False
        )

    tolerance: bpy.props.FloatProperty(
        name = "Tolerance",
        subtype='DISTANCE',
        default = 0.000001,
        min = 0.0,
        max = 0.1,
        description = "Distance tolerance between coplanar faces",
        unit='LENGTH'
        )

    angle: bpy.props.FloatProperty(
        name = "Angle",
        subtype='ANGLE',
        default = radians(0.1),
        min = radians(0.0),
        max = radians(90.0),
        description = "Angle tolerance between coplanar faces",
        )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        self.select_overlapping(context, self.overlapping, self.distance, self.intersections, self.inset, self.coplanar, self.tolerance, self.angle)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.select_type = get_mesh_select_mode()
        self.execute(context)
        return {"FINISHED"}

    def draw(self, context):
        mesh_select_mode = get_mesh_select_mode()
        face_mode = mesh_select_mode == 'FACE'
        
        if self.select_type != mesh_select_mode:
            self.select_type = mesh_select_mode
        
        layout = self.layout
        scene = context.scene

        #box = layout.box()
        row = layout.row()
        row.label(text="Selection Type:")
        row.prop(self, "select_type", text="")

        layout.separator()

        # overlapping
        box = layout.box()
        row = box.row()
        row.label(text="Doubles")
        row.prop(self, "overlapping", text="")
        distance_row = box.row()
        distance_row.enabled = self.overlapping
        distance_row.label(text="Distance")
        distance_row.prop(self, "distance", text="")

        # Intersections
        box = layout.box()
        box.enabled = face_mode
        row = box.row()
        row.label(text="Intersections")
        row.prop(self, "intersections", text="")

        distance_row = box.row()
        distance_row.enabled = self.intersections
        distance_row.label(text="Inset")
        distance_row.prop(self, "inset", text="")

        # Coplanar
        box = layout.box()
        box.enabled = face_mode
        row = box.row()
        row.label(text="Coplanar")
        row.prop(self, "coplanar", text="")
        
        distance_row = box.row()
        distance_row.enabled = self.coplanar
        distance_row.label(text="Tolerance")
        distance_row.prop(self, "tolerance", text="")

        distance_row = box.row()
        distance_row.enabled = self.coplanar
        distance_row.label(text="Angle")
        distance_row.prop(self, "angle", text="")

    def select_overlapping(self, context, overlapping, distance, intersections, inset, coplanar, tolerance, angle):
        # Selection mode - Vertex, Edge, Face
        if self.select_type == 'VERT':
            bpy.context.tool_settings.mesh_select_mode = [True, False, False]
        elif self.select_type == 'EDGE':
            bpy.context.tool_settings.mesh_select_mode = [False, True, False]
        elif self.select_type == 'FACE':
            bpy.context.tool_settings.mesh_select_mode = [False, False, True]                    

        # Deselect all first
        #bpy.ops.mesh.select_all(action = 'DESELECT')

        # force context update in edit mode
        # apparently there's a bug in scene.update()
        bpy.context.scene.update()
        mode = bpy.context.object.mode
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
            bpy.ops.object.mode_set(mode = mode)

        # select in context
        (vertex_mode, edge_mode, face_mode) = bpy.context.tool_settings.mesh_select_mode

        if overlapping:
            # vertex mode
            if vertex_mode:
                if context.active_object.data.vertices:
                    select_duplicate_vertices(context, distance)        
            # edge mode
            elif edge_mode:
                if context.active_object.data.edges:
                    select_duplicate_edges(context, distance)
            # face mode
            elif face_mode:
                if context.active_object.data.polygons:
                    select_duplicate_faces(context, distance)

        if (intersections or coplanar) and face_mode:
            if context.active_object.data.polygons:
                select_intersect_faces(context, intersections, coplanar, inset, tolerance, angle)

def menu_func(self, context):
    self.layout.operator(SelectOverlapping.bl_idname, text="Select Overlapping")

def register():
   bpy.utils.register_class(SelectOverlapping)
   bpy.types.VIEW3D_MT_edit_mesh_select_by_trait.append(menu_func)

def unregister():
    bpy.utils.unregister_class(SelectOverlapping)
    bpy.types.VIEW3D_MT_edit_mesh_select_by_trait.remove(menu_func)

if __name__ == "__main__":
    register()
