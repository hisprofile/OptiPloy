import bpy, os, subprocess, threading

blender_bin = bpy.app.binary_path
folder = os.path.dirname(__file__)
receiver = os.path.join(folder, 'receiver.py')

active_thread = None

def run_instance():
    global active_thread
    #if active_thread:
    #    return
    subprocess.run([blender_bin,
                    '--factory-startup',
                    '--background',
                    f'--python', receiver
                        ])
    active_thread = None

def register():
    global active_thread
    if bpy.app.background:
        return
    #if active_thread:
    #    return
    print('calling 2!')
    T = threading.Thread(target=run_instance, daemon=True)
    T.start()
    active_thread = T