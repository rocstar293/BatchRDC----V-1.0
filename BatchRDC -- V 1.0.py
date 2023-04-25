import bpy, os, bmesh
import time

'''
RDC Batch Importer

By: Tyler Beaird
Script Verison: 1.0.1
Blender Version: 3.0.1

RenderDoc Version: 1.13


=== SETUP ===

The script requires the following Folder Structure:
    - Project Folder
    |   - MOD
    |   |   - Context Capture
    |   |   |   - Blender Project (.blend)
    |   |   |   - RDC (Folder)
    |   |   |   |   - 001.rdc
    |   |   |   |   - 002.rdc
    |   |   |   |   - 003.rdc

As shown above, the RDC folder needs to be placed in the same directory as the .blend file for the script to work.

RDC files will load in and merge in numerical order, the only requirement is that every RDC File shares some overlap with one or more preceding tiles. 

    For Example:

        === Valid === -----------------------------------------------------  
        
        +===+===+===+       
        | 1 | 2 | 3 |       
        +---+---+---+       This will work because every tile
        | 4 | 5 | 6 |       shares an overlap with one
        +---+---+---+       or more of it's preceding tiles
        | 7 | 8 | 9 |
        +===+===+===+ 
 
        == Invalid == -----------------------------------------------------  
                             
        +===+===+===+       
        | 1 | 2 | 3 |       In this example, because tile 4 imports before 
        +---+---+---+       either of it's neighbors (7, 5), the script 
        | 7 | 8 | 9 |       will fail, as tile 4 does not have any  
        +---+---+---+       information to merge itself to 
        | 4 | 5 | 6 |       the preceding capture.
        +===+===+===+

'''

# String padding for console output
def padded(string, border ="|", orientation="c"):
    
    if orientation == "c":
        output = (string.center(35, " "))
    
    elif orientation == "l":
        output = (string.ljust(35, " "))
    
    elif orientation == "r":
        output = (string.rjust(35, " "))
    
    return f"{border}{output}{border}"


# Add a named collection as child of specified parent; sets context active collection
def create_col(parent_layer_collection, collection_name):
    
    new_col = bpy.data.collections.new(collection_name)
    parent_layer_collection.collection.children.link(new_col)
    new_child_layer_col = parent_layer_collection.children.get(new_col.name)
    
    bpy.context.view_layer.active_layer_collection = new_child_layer_col
    
    return new_child_layer_col


# Perform vertex optimiziation to all meshes in active collection
def minimize_vert_count(context):
   
  initial_verts = 0
  final_verts = 0
  meshes = set(o.data for o in context.collection.all_objects if o.type == 'MESH')
  
  bm = bmesh.new()
  for m in meshes:
    bm.from_mesh(m)
    initial_verts += len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1)
    vert_list = [v for v in bm.verts if v.is_manifold == False and v.is_boundary == False and v.is_wire == True]
    bmesh.ops.delete(bm, geom=vert_list, context='VERTS')
    final_verts += len(bm.verts)
    bm.to_mesh(m)
    bm.clear()


master_collection = bpy.context.view_layer.active_layer_collection # Capture will be stored in active collection

# Gets an ordered list of RDC files for import
filepath = os.path.dirname(bpy.data.filepath)
rdc_path = filepath+"\RDC"
files = sorted([f for f in os.listdir(rdc_path) if ".rdc" in f], key = lambda f: f.split(".")[0])
f_len = len(files)


# Ensures a directory for saved textures
texpath = filepath + "\Textures"
if not os.path.isdir(texpath):
    os.mkdir(texpath)

if bpy.app.version_string != "3.0.1":
    print(f"****** WARNING ******\nThis script was written for Blender 3.0.1\nCurrent version: {bpy.app.version_string}\n")

print("=====================================")
print(padded("BatchRDC -- V 1.0"))
print("|===================================|")

col_list = [] # List of all RDC collections
script_start_time = time.time()


# For each RDC file, Create a collection under master and import the RDC file
for i, f in enumerate(files):
    
    print(padded(f"Importing {f} ({i+1}/{f_len})"))
    start_time = time.time()
    
    path = f"{rdc_path}\\{f}"
    file_col = create_col(master_collection, f)
    
    col_list.append(file_col)
    
    bpy.ops.import_rdc.google_maps(filepath=path, filter_glob=".rdc", max_blocks=-1)
    print(padded(f"{f} imported ({round(time.time() - start_time, 2)} s)"))


    
col_obj_ref = [] # Contains a list of objects for each collection

if len(col_list) > 1: # If importing multiple RDC files, Duplicate blocks will be removed, 
    
    for i in range(0, len(col_list)-1):
    
        for obj in bpy.context.selected_objects: # Clear selection
            obj.select_set(False)

        # Define 
        this_col = col_list[i].collection
        next_col = col_list[i+1].collection
        next_objs = list(next_col.objects)
    
        if i == 0:
            col_obj_ref.append(list(this_col.objects))
    
        this_col.objects[0].select_set(True)
        bpy.context.view_layer.objects.active = next_objs[0]

        bpy.ops.object.lily_capture_merger()
        
        col_objs = []
        col_obj_ref.append(col_objs)
        
        for obj in this_col.objects:
            this_col.objects.unlink(obj)
            next_col.objects.link(obj)
            
        for obj in next_objs:
            col_objs.append(obj)
    
else:
    
    col_obj_ref.append(list(col_list[0].collection.objects))        

for ii, col in enumerate(col_obj_ref):
    
    valid_objs = []
    
    for i, obj in enumerate(col):
        
        try: 
            x = obj.type
            valid_objs.append(obj)
        except:
            pass
        col = valid_objs
    print(padded(f"valid_objs: {len(valid_objs)}"))
    
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    
    for obj in col:
        obj.select_set(True)
    
    bpy.context.view_layer.objects.active = col[0]
    
    active = bpy.context.active_object
    active.name = f"Map {ii}"
    
    bpy.ops.object.lily_texture_packer()
    bpy.ops.object.make_links_data(type='MATERIAL')
    print(padded(f"packed texture"))
    
    mat = active.material_slots[0].material
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    img = nodes[2].image
    newimage = f"{texpath}\\{bpy.path.display_name_from_filepath(bpy.data.filepath)}_{active.name}.jpg"
    img.filepath_raw = newimage
    img.file_format = "JPEG"
    img.save()
    img = newimage
    mat.name = active.name
    print(padded(f"saved_image: {newimage}"))
    
    bpy.ops.object.join()
    minimize_vert_count(bpy.context)
    
capture = create_col(master_collection, "Capture")

for obj in col_list[-1].collection.objects:
    col_list[-1].collection.objects.unlink(obj)
    capture.collection.objects.link(obj)
    
for col in col_list:
    bpy.data.collections.remove(col.collection)

print(padded(f"BatchRDC Finished:"))
print(padded(f"Imported {f_len} files in {round(time.time() - script_start_time, 2)} s"))
