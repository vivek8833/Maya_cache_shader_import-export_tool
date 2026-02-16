import os
import sys
import json
import maya.cmds as cmds


def validate_json_path(json_path):
    if not json_path:
        raise RuntimeError("No JSON path provided.")

    if not json_path.endswith("scene_lit.json"):
        raise RuntimeError("JSON file must end with 'scene_lit.json'")

    if not os.path.exists(json_path):
        raise RuntimeError(f"JSON file not found: {json_path}")

    return json_path


def load_json(json_path):
    with open(json_path, "r") as f:
        return json.load(f)


def apply_scene_settings(file_info):
    fps = file_info.get("fps")
    start = file_info["frame_range"]["start_frame"]
    end = file_info["frame_range"]["end_frame"]
    cmds.currentUnit(time=fps)
    cmds.playbackOptions(min=start, max=end)

def reference_file(path, file_type, namespace):
    if not os.path.exists(path):
        print("File not found:", path)
        return None

    return cmds.file(
        path,
        r=True,
        type=file_type,
        ignoreVersion=True,
        mergeNamespacesOnClash=False,
        gl=True,
        namespace=namespace,
        options="v=0;"
    )


def assignshaders(shader_file_info=None,
                  ref_name_space=None,
                  shading_namespace=None):
    if not os.path.exists(shader_file_info):
        print("Shader info json missing:", shader_file_info)
        return

    cmds.editRenderLayerGlobals(currentRenderLayer='defaultRenderLayer')

    with open(shader_file_info) as f:
        json_data = json.load(f)

    for shdengin, info in json_data.items():

        for mesh in info.get("dag_nodes", []):

            try:
                mesh = f"{ref_name_space}:{mesh}"

                if not cmds.objExists(mesh):
                    print("Object not found:", mesh)
                    continue

                cmds.select(mesh)
                cmds.hyperShade(assign=f"{shading_namespace}:{shdengin}")
                cmds.select(cl=True)

            except Exception as e:
                print("Shader assign error:", mesh, e)


def process_scene(json_path):
    for each in ['AbcExport.mll', 'AbcImport.mll', 'atomImportExport.mll',
                 'vrayformaya.mll', 'modelingToolkit.mll']:
        if not cmds.pluginInfo(each, q=True, l=True):
            try:
                cmds.loadPlugin(each)
            except:
                pass

    json_path = validate_json_path(json_path)
    data = load_json(json_path)

    apply_scene_settings(data["File_info"])

    cache_shader_info = data["Cache_shader_info"]

    for asset_name, info in cache_shader_info.items():
        base_namespace = info["namespace"]
        cache_namespace = f"{base_namespace}_cache"
        shader_namespace = f"{base_namespace}_shader"

        reference_file(
            info["cache_file_path"],
            "Alembic",
            cache_namespace
        )

        reference_file(
            info["shader_file_path"],
            info["shader_type"],
            shader_namespace
        )

        assignshaders(
            shader_file_info=info["shader_file_info"],
            ref_name_space=cache_namespace,
            shading_namespace=shader_namespace
        )

    print("\nCache + Shader reference process completed.")


if __name__ == "__main__":

    if "json_path" not in globals():
        raise RuntimeError("json_path not injected from launcher.")
    print("Using JSON:", json_path)
    try:
        process_scene(json_path)
        print("Cache + Shader build completed successfully.")
    except Exception as e:
        print("Cache + Shader build failed:", e)
        raise
