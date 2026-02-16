import os
import sys
import re
import maya.mel as mel
import maya.cmds as cmds
import json


class shader_ex:
    def __init__(self):
        for each in ['AbcExport.mll', 'AbcImport.mll', 'atomImportExport.mll',
                     'vrayformaya.mll', 'modelingToolkit.mll']:
            if not cmds.pluginInfo(each, q=True, l=True):
                try:
                    cmds.loadPlugin(each)
                except:
                    pass

    def export_uvs(self, type=None, path=None):
        uv_data = {}
        meshes = []

        if type == 'all':
            meshes = cmds.listRelatives(
                cmds.ls(type='mesh', l=True, ni=True),
                p=True, f=True, type='transform'
            )

        if not meshes:
            return

        for mesh in meshes:
            if re.search(r'\|mash_grp|\|mash', mesh, re.I):
                continue
            data = UVManager().getUVData(mesh)
            uv_data.setdefault(mesh, data)

        UVManager().write(path, uv_data)

    def getShaders(self, scene_path=None):
        if scene_path:
            if not os.path.exists(scene_path):
                raise RuntimeError(f"Scene file not found: {scene_path}")
            cmds.file(scene_path, open=True, force=True)
        scene_path = cmds.file(q=True, sn=True)
        curves = cmds.ls(type="nurbsCurve")
        if curves:
            curve_transforms = cmds.listRelatives(curves, parent=True, fullPath=True)
            curve_transforms = list(set(curve_transforms))
            cmds.delete(curve_transforms)
            print("Deleted NURBS Curves:", len(curve_transforms))
        else:
            print("No NURBS Curves found.")
        transforms = cmds.ls(type="transform", long=True)
        empty_groups = []
        for node in transforms:
            children = cmds.listRelatives(node, children=True)
            if not children:
                empty_groups.append(node)

        if empty_groups:
            cmds.delete(empty_groups)
            print("Deleted Empty Groups:", len(empty_groups))
        else:
            print("No Empty Groups found.")

        scene_dir = os.path.dirname(scene_path)
        basename = os.path.splitext(os.path.basename(scene_path))[0]
        Shader_folder = os.path.join(scene_dir, f"Shader_{basename}")

        # Create folder if it doesn't exist
        if not os.path.exists(Shader_folder):
            os.makedirs(Shader_folder)

        cmds.select(mel.eval('lsThroughFilter DefaultShadingGroupsAndMaterialsFilter;'), ne=True)
        shader_file_name = f"{basename}.ma"
        shader_file_path = os.path.join(Shader_folder, shader_file_name).replace("\\", "/")
        cmds.file(shader_file_path, options="v=0;", typ="mayaAscii", pr=False, es=True, force=True)
        cmds.select(cl=True)

        connection_info_path = os.path.join(Shader_folder, "info_shader.json")
        uv_export_path = os.path.join(Shader_folder, "uvinfo.json")

        final_dict = {}
        shading_engines = cmds.ls(type='shadingEngine')

        for shEngine in shading_engines:
            final_dict[shEngine] = {"shaders": [], "dag_nodes": []}

            connections = cmds.listConnections(shEngine) or []
            for connection in connections:
                inherited_types = cmds.nodeType(connection, inherited=True) or []
                if 'shadingDependNode' in inherited_types:
                    final_dict[shEngine]["shaders"].append(connection)

            members = cmds.sets(shEngine, q=True) or []
            for member in members:
                parent = cmds.pickWalk(member, d='up')
                if parent:
                    final_dict[shEngine]["dag_nodes"].append(parent[0])

        with open(connection_info_path, 'w') as f:
            json.dump(final_dict, f, indent=4)

        print("Shader export completed successfully")
        print("Shader path:", shader_file_path)
        print("Connection info path:", connection_info_path)
        cmds.file(shader_file_path, options="v=0;", typ="mayaAscii", pr=False, es=True, force=True)
        return shader_file_path, connection_info_path, uv_export_path
    def maya_close(self):
        print("Process Completed Successfully.")
        cmds.refresh(force=True)
        cmds.quit(force=True)
        cmds.evalDeferred('cmds.quit(abort=True,f=True)')


if __name__ == "__main__":
    shader = shader_ex()
    try:
        shader.getShaders(scene_path)
    except NameError:
        try:
            shader.getShaders()
            import time
            time.sleep(6)
            shader.maya_close()
        except Exception as e:
            print("Error during shader export:", e)
    except Exception as e:
        print("Error during shader export:", e)
