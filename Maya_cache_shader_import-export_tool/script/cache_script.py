import re
import maya.cmds as cmds
import maya.mel as mel
import os
import json

class ExportAlembic:
    def __init__(self):
        for plugin in ['AbcExport.mll', 'AbcImport.mll', 'fbxmaya.mll']:
            if not cmds.pluginInfo(plugin, q=True, l=True):
                try:
                    cmds.loadPlugin(plugin)
                except:
                    pass

    def open_maya(self, scene_path=None):

        if scene_path:
            if not os.path.exists(scene_path):
                raise RuntimeError(f"Scene file not found: {scene_path}")
            cmds.file(scene_path, open=True, force=True)

        self.bakeConstraints()

        scene_path = cmds.file(q=True, sn=True)
        if not scene_path:
            cmds.error("Scene is not saved. Please save the scene first.")
        scene_dir = os.path.dirname(scene_path)
        scene_name = os.path.splitext(os.path.basename(scene_path))[0]
        cache_folder_name = "Cache_{}".format(scene_name)
        cache_file_dir = os.path.join(scene_dir, cache_folder_name).replace("\\", "/")
        if not os.path.exists(cache_file_dir):
            os.makedirs(cache_file_dir)
        print("Cache Directory:", cache_file_dir)
        self.shot_first_frame = cmds.playbackOptions(min=True, q=True)
        self.shot_last_frame = cmds.playbackOptions(max=True, q=True)
        alembic_cmd_list = []
        for panel in cmds.getPanel(all=True):
            if panel.startswith('modelPanel'):
                cmds.modelEditor(panel, e=True, displayAppearance='boundingBox')

        for each in cmds.file(r=True, q=True):
            namespace = cmds.file(each, namespace=True, q=True)
            cache_file_path_local = "%s/%s.abc" % (cache_file_dir, os.path.basename(each).replace(".ma", ""))
            cache_node = '%s:Cache' % namespace if cmds.objExists('%s:Cache' % namespace) else '%s:cache' % namespace
            cache_node_connection = cmds.listConnections(cache_node, s=True, d=False) or []
            if cache_node_connection:
                cache_nodes = ""
                for cache_set in cache_node_connection:
                    cmds.select(cache_set)
                    # nodeName = cmds.ls(sl=True)[0]
                    cache_nodes += " -root " + cache_set
                alembic_cmd_list.append(
                    "-frameRange " + str(self.shot_first_frame) + " " + str(self.shot_last_frame) +
                    " -stripNamespaces -uvWrite -writeFaceSets -worldSpace -writeVisibility -dataFormat ogawa "
                    + cache_nodes +
                    " -file " + "\"%s\"" % cache_file_path_local)

            try:
                frist_cam = [each for each in cmds.listCameras() if
                             not cmds.referenceQuery(each, inr=True) and not re.search(r"front|persp|side|top", each,
                                                                                       re.I)]
                frist_cam = frist_cam[0]
                cmds.select(frist_cam)
                cache_file_path_local = "%s/%s.abc" % (cache_file_dir, frist_cam)
                cache_nodes = ""
                cache_nodes += " -root |" + frist_cam

                cmds.bakeResults('%s' % frist_cam, simulation=True, t=(self.shot_first_frame, self.shot_last_frame),
                                 hierarchy='below', sampleBy=1, disableImplicitControl=True,
                                 preserveOutsideKeys=True, sparseAnimCurveBake=False,
                                 removeBakedAttributeFromLayer=False, removeBakedAnimFromLayer=False,
                                 bakeOnOverrideLayer=False, minimizeRotation=True, controlPoints=False,
                                 shape=True)

                alembic_cmd_list.append(
                    "-frameRange " + str(self.shot_first_frame) + " " + str(self.shot_last_frame) +
                    " -stripNamespaces -uvWrite -writeFaceSets -worldSpace -writeVisibility -dataFormat ogawa "
                    + cache_nodes +
                    " -file " + "\"%s\"" % cache_file_path_local)
                print('alembic_cmd_list++++++', alembic_cmd_list)
            except Exception as error:
                print(error)

        try:
            cmds.AbcExport(j=alembic_cmd_list)
        except Exception as error:
            print("Exception on alembic cache +++++ ", error)

        json_file_path = os.path.join(cache_file_dir, "scene_lit.json").replace("\\", "/")
        fps = cmds.currentUnit(q=True, time=True)
        maya_version = cmds.about(version=True)
        scene_path = cmds.file(q=True, sn=True)
        file_info_dict = {
            "fps": fps,
            "maya_version": maya_version,
            "scene_path": scene_path,
            "frame_range": {
                "start_frame": self.shot_first_frame,
                "end_frame": self.shot_last_frame
            }
        }
        cache_shader_info = {}
        for each_ref_path in cmds.file(q=True, r=True):
            try:
                namespace = cmds.referenceQuery(each_ref_path, namespace=True)
                if namespace.startswith(":"):
                    namespace = namespace[1:]
            except:
                continue
            ref_node_name = namespace
            cache_file_path_local = "%s/%s.abc" % (
                cache_file_dir,
                os.path.basename(each_ref_path).replace(".ma", "")
            )
            cache_node = '%s:Cache' % namespace if cmds.objExists('%s:Cache' % namespace) else '%s:cache' % namespace
            cache_node_connection = cmds.listConnections(cache_node, s=True, d=False) or []
            cache_sets_clean = [node.split("|")[-1] for node in cache_node_connection]
            scene_dir = os.path.dirname(scene_path)
            shader_folder_name = "Shader_{}".format(namespace)
            shader_folder_path = os.path.join(scene_dir, shader_folder_name).replace("\\", "/")
            shader_file_path = os.path.join(shader_folder_path, "{}.ma".format(namespace)).replace("\\", "/")
            shader_file_info = os.path.join(shader_folder_path, "info_shader.json").replace("\\", "/")

            cache_shader_info[ref_node_name] = {
                "ref_file": each_ref_path,
                "cache_file_path": cache_file_path_local,
                "cache_set": cache_sets_clean,
                "shader_file_path": shader_file_path,
                "shader_file_info": shader_file_info,
                "cache_type": "alembic",
                "shader_type": "mayaAscii",
                "namespace": namespace
            }

        final_json_dict = {
            "File_info": file_info_dict,
            "Cache_shader_info": cache_shader_info
        }

        with open(json_file_path, "w") as json_file:
            json.dump(final_json_dict, json_file, indent=4)
        print("JSON Exported Successfully:", json_file_path)

    def bakeConstraints(self):
        cmds.select(cl=True)
        all_controls = []
        for each_ref_path in cmds.file(q=True, r=True):
            try:
                namespace = cmds.referenceQuery(each_ref_path, namespace=True)
                if namespace.startswith(":"):
                    namespace = namespace[1:]
            except:
                continue
            curves = cmds.ls(namespace + ":*", type="nurbsCurve", long=True)
            for curve in curves:
                parent = cmds.listRelatives(curve, p=True, f=True)
                if parent:
                    all_controls.append(parent[0])
        all_controls = list(set(all_controls))
        if not all_controls:
            print("No referenced controls found.")
            return
        cmds.select(all_controls)
        try:
            start_frame = cmds.playbackOptions(q=True, min=True)
            end_frame = cmds.playbackOptions(q=True, max=True)
            current_pane = cmds.getPanel(withFocus=True)
            if cmds.getPanel(typeOf=current_pane) == "modelPanel":
                cmds.modelEditor(current_pane, edit=True, alo=False)
            cmds.bakeResults(
                simulation=True,
                t=(start_frame, end_frame),
                sb=1,
                disableImplicitControl=True,
                preserveOutsideKeys=True,
                sparseAnimCurveBake=False,
                removeBakedAttributeFromLayer=False,
                removeBakedAnimFromLayer=False,
                bakeOnOverrideLayer=False,
                minimizeRotation=True,
                controlPoints=False,
                shape=False
            )
            cmds.select(cl=True)
            print("Bake Completed Successfully")
        except Exception:
            print("Error in baking")
            print(sys.exc_info())

    def maya_close(self):
        cmds.evalDeferred('cmds.quit(abort=True,f=True)')


if __name__ == "__main__":
    cache_process = ExportAlembic()
    try:
        cache_process.open_maya(scene_path)
    except NameError:
        try:
            cache_process.open_maya()
            import time
            time.sleep(10)
            cache_process.maya_close()
        except Exception as e:
            print("Error during Cache export:", e)
    except Exception as e:
        print("Error during Cache export:", e)
    finally:
        print("Cache export completed successfully")
        try:
            cmds.evalDeferred('cmds.quit(abort=True,f=True)')
        except Exception as e:
            print("Error during Exception is:", e)
