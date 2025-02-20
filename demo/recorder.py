import pybullet as p
import PySimpleGUI as sg
import pickle
from os import getcwd
from urdfpy import URDF
from os.path import abspath, dirname, basename, splitext
from numpy import array, matmul
from transforms3d.affines import decompose
from transforms3d.quaternions import mat2quat


class PybulletRecorder:
    class LinkTracker:
        def __init__(self,
                     name,
                     body_id,
                     link_id,
                     link_origin,
                     mesh_path,
                     mesh_scale):
            self.body_id = body_id
            self.link_id = link_id
            self.mesh_path = mesh_path
            self.mesh_scale = mesh_scale
            decomposed_origin = decompose(link_origin)
            orn = mat2quat(decomposed_origin[1])
            orn = [orn[1], orn[2], orn[3], orn[0]]
            self.link_pose = [decomposed_origin[0],
                              orn]
            self.name = name

        def transform(self, position, orientation):
            return p.multiplyTransforms(
                position, orientation,
                self.link_pose[0], self.link_pose[1],
            )

        def get_keyframe(self):
            if self.link_id == -1:
                position, orientation = p.getBasePositionAndOrientation(
                    self.body_id)
                position, orientation = self.transform(
                    position=position, orientation=orientation)
            else:
                link_state = p.getLinkState(self.body_id,
                                            self.link_id,
                                            computeForwardKinematics=True)
                position, orientation = self.transform(
                    position=link_state[4],
                    orientation=link_state[5])
            return {
                'position': list(position),
                'orientation': list(orientation)
            }

    def __init__(self):
        self.states = []
        self.links = []

    def register_object(self, body_id, path):
        full_path = abspath(path)
        dir_path = dirname(full_path)
        file_name = splitext(basename(path))[0]
        robot = URDF.load(path)
        num_joints = p.getNumJoints(body_id)
        assert num_joints + 1 == len(robot.links)
        if len(robot.links) == 1:
            self.links.append(
                PybulletRecorder.LinkTracker(
                    name=file_name + f'_{body_id}_root',
                    body_id=body_id,
                    link_id=-1,
                    link_origin=robot.links[0].visuals[0].origin,
                    mesh_path=dir_path + '/' +
                    robot.links[0].visuals[0].geometry.mesh.filename,
                    mesh_scale=robot.links[0].visuals[0].geometry.mesh.scale))
        else:
            self.links.append(
                PybulletRecorder.LinkTracker(
                    name=file_name + f'_{body_id}_root',
                    body_id=body_id,
                    link_id=-1,
                    link_origin=robot.links[0].visuals[0].origin,
                    mesh_path=dir_path + '/' +
                    robot.links[0].visuals[0].geometry.mesh.filename,
                    mesh_scale=robot.links[0].visuals[0].geometry.mesh.scale))
            for link_id, link in enumerate(robot.links):
                if len(link.visuals) > 0:
                    if link_id > 7:
                        link_id -= 3
                    if p.getLinkState(body_id, link_id) is not None\
                            and link.visuals[0].geometry.mesh:
                        # hard code for robotiq
                        self.links.append(
                            PybulletRecorder.LinkTracker(
                                name=file_name + f'_{body_id}_{link.name}',
                                body_id=body_id,
                                link_id=link_id,
                                link_origin=link.visuals[0].origin,
                                mesh_path=dir_path + '/' +
                                link.visuals[0].geometry.mesh.filename,
                                mesh_scale=link.visuals[0].geometry.mesh.scale))

    def add_keyframe(self):
        # Ideally, call every stepSimulation
        current_state = {}
        for link in self.links:
            current_state[link.name] = link.get_keyframe()
        self.states.append(current_state)

    def prompt_save(self):
        layout = [[sg.Text('Do you want to save previous episode?')],
                  [sg.Button('Yes'), sg.Button('No')]]
        window = sg.Window('PyBullet Recorder', layout)
        save = False
        while True:
            event, values = window.read()
            if event in (None, 'No'):
                break
            elif event == 'Yes':
                save = True
                break
        window.close()
        if save:
            layout = [[sg.Text('Where do you want to save it?')],
                      [sg.Text('Path'), sg.InputText(getcwd())],
                      [sg.Button('OK')]]
            window = sg.Window('PyBullet Recorder', layout)
            event, values = window.read()
            window.close()
            self.save(values[0])
        self.reset()

    def reset(self):
        self.states = []

    def get_formatted_output(self):
        retval = {}
        for link in self.links:
            retval[link.name] = {
                'type': 'mesh',
                'mesh_path': link.mesh_path,
                'mesh_scale': link.mesh_scale,
                'frames': [state[link.name] for state in self.states]
            }
        return retval

    def save(self, path):
        if path is None:
            print("[Recorder] Path is None.. not saving")
        else:
            print("[Recorder] Saving state to {}".format(path))
            pickle.dump(self.get_formatted_output(), open(path, 'wb'))
