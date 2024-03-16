from math import pi, sin, cos

from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock
from direct.task.TaskManagerGlobal import taskMgr
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import loadPrcFile
from panda3d.core import DirectionalLight, AmbientLight
from panda3d.core import TransparencyAttrib
from panda3d.core import WindowProperties
from panda3d.core import CollisionTraverser, CollisionNode, CollisionBox, CollisionRay, CollisionHandlerQueue

loadPrcFile('settings.prc')


def degrees_to_radians(degrees):
    return degrees * (pi / 180.0)


class MyGame(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.ray_queue = None

        # initialize blocks
        self.slime_block = None
        self.sand_block = None
        self.stone_block = None
        self.dirt_block = None
        self.grass_block = None

        self.selectedBlockType = 'grass'

        # initialize ke_map for controls
        self.key_map = None
        self.camera_swing_factor = None
        self.camera_swing_activated = None
        self.lastMouseX = None
        self.lastMouseY = None

        self.load_models()
        self.setup_lights()
        self.generate_terrain()
        self.setup_camera()
        self.setup_skybox()
        self.capture_mouse()
        self.setup_controls()

        taskMgr.add(self.update, 'update')

    def update(self, task):
        dt = globalClock.getDt()

        player_move_speed = 10

        x_movement = 0
        y_movement = 0
        z_movement = 0

        if self.key_map['forward']:
            x_movement -= dt * player_move_speed * sin(degrees_to_radians(self.camera.getH()))
            y_movement += dt * player_move_speed * cos(degrees_to_radians(self.camera.getH()))
        if self.key_map['backward']:
            x_movement += dt * player_move_speed * sin(degrees_to_radians(self.camera.getH()))
            y_movement -= dt * player_move_speed * cos(degrees_to_radians(self.camera.getH()))
        if self.key_map['left']:
            x_movement -= dt * player_move_speed * cos(degrees_to_radians(self.camera.getH()))
            y_movement -= dt * player_move_speed * sin(degrees_to_radians(self.camera.getH()))
        if self.key_map['right']:
            x_movement += dt * player_move_speed * cos(degrees_to_radians(self.camera.getH()))
            y_movement += dt * player_move_speed * sin(degrees_to_radians(self.camera.getH()))
        if self.key_map['up']:
            z_movement += dt * player_move_speed
        if self.key_map['down']:
            z_movement -= dt * player_move_speed

        self.camera.setPos(
            self.camera.getX() + x_movement,
            self.camera.getY() + y_movement,
            self.camera.getZ() + z_movement,
        )

        if self.camera_swing_activated:
            md = self.win.getPointer(0)
            mouse_x = md.getX()
            mouse_y = md.getY()

            mouse_change_x = mouse_x - self.lastMouseX
            mouse_change_y = mouse_y - self.lastMouseY

            self.camera_swing_factor = 10

            current_h = self.camera.getH()
            current_p = self.camera.getP()

            self.camera.setHpr(
                current_h - mouse_change_x * dt * self.camera_swing_factor,
                min(90, max(-90, current_p - mouse_change_y * dt * self.camera_swing_factor)),
                0
            )

            self.lastMouseX = mouse_x
            self.lastMouseY = mouse_y

        return task.cont

    def setup_controls(self):
        self.key_map = {
            "forward": False,
            "backward": False,
            "left": False,
            "right": False,
            "up": False,
            "down": False,
        }

        self.accept('escape', self.release_mouse)
        self.accept('mouse1', self.handle_left_click)
        self.accept('mouse3', self.place_block)

        self.accept('w', self.update_key_map, ['forward', True])
        self.accept('w-up', self.update_key_map, ['forward', False])
        self.accept('a', self.update_key_map, ['left', True])
        self.accept('a-up', self.update_key_map, ['left', False])
        self.accept('s', self.update_key_map, ['backward', True])
        self.accept('s-up', self.update_key_map, ['backward', False])
        self.accept('d', self.update_key_map, ['right', True])
        self.accept('d-up', self.update_key_map, ['right', False])
        self.accept('space', self.update_key_map, ['up', True])
        self.accept('space-up', self.update_key_map, ['up', False])
        self.accept('lshift', self.update_key_map, ['down', True])
        self.accept('lshift-up', self.update_key_map, ['down', False])

        self.accept('1', self.set_selected_block_type, ['grass'])
        self.accept('2', self.set_selected_block_type, ['dirt'])
        self.accept('3', self.set_selected_block_type, ['sand'])
        self.accept('4', self.set_selected_block_type, ['stone'])
        self.accept('5', self.set_selected_block_type, ['slime'])

    def set_selected_block_type(self, block_type):
        self.selectedBlockType = block_type

    def handle_left_click(self):
        self.capture_mouse()
        self.remove_block()

    def remove_block(self):
        if self.ray_queue.getNumEntries() > 0:
            self.ray_queue.sortEntries()
            ray_hit = self.ray_queue.getEntry(0)

            hit_node_path = ray_hit.getIntoNodePath()
            hit_object = hit_node_path.getPythonTag('owner')
            distance_from_player = hit_object.getDistance(self.camera)

            if distance_from_player < 12:
                hit_node_path.clearPythonTag('owner')
                hit_object.removeNode()

    def place_block(self):
        if self.ray_queue.getNumEntries() > 0:
            self.ray_queue.sortEntries()
            ray_hit = self.ray_queue.getEntry(0)
            hit_node_path = ray_hit.getIntoNodePath()
            normal = ray_hit.getSurfaceNormal(hit_node_path)
            hit_object = hit_node_path.getPythonTag('owner')
            distance_from_player = hit_object.getDistance(self.camera)

            if distance_from_player < 14:
                hit_block_pos = hit_object.getPos()
                new_block_pos = hit_block_pos + normal * 2
                self.create_new_block(new_block_pos.x, new_block_pos.y, new_block_pos.z, self.selectedBlockType)

    def update_key_map(self, key, value):
        self.key_map[key] = value

    def capture_mouse(self):
        self.camera_swing_activated = True

        md = self.win.getPointer(0)
        self.lastMouseX = md.getX()
        self.lastMouseY = md.getY()

        properties = WindowProperties()
        properties.setIconFilename("python4gaming.ico")
        properties.setTitle("Python 4 Gaming")
        properties.setCursorHidden(True)
        properties.setMouseMode(WindowProperties.M_relative)
        self.win.requestProperties(properties)

    def release_mouse(self):
        self.camera_swing_activated = False

        properties = WindowProperties()
        properties.setCursorHidden(False)
        properties.setMouseMode(WindowProperties.M_absolute)
        self.win.requestProperties(properties)

    def setup_camera(self):
        self.disableMouse()
        self.camera.setPos(0, 0, 3)
        self.camLens.setFov(80)

        crosshairs = OnscreenImage(
            image='crosshairs.png',
            pos=(0, 0, 0),
            scale=0.05,
        )
        crosshairs.setTransparency(TransparencyAttrib.MAlpha)

        self.cTrav = CollisionTraverser()
        ray = CollisionRay()
        ray.setFromLens(self.camNode, (0, 0))
        ray_node = CollisionNode('line-of-sight')
        ray_node.addSolid(ray)
        ray_node_path = self.camera.attachNewNode(ray_node)
        self.ray_queue = CollisionHandlerQueue()
        self.cTrav.addCollider(ray_node_path, self.ray_queue)

    def setup_skybox(self):
        skybox = self.loader.loadModel('skybox/skybox.egg')
        skybox.setScale(500)
        skybox.setBin('background', 1)
        skybox.setDepthWrite(0)
        skybox.setLightOff()
        skybox.reparentTo(self.render)

    def generate_terrain(self):
        for z in range(10):
            for y in range(40):
                for x in range(40):
                    self.create_new_block(
                        x * 2 - 20,
                        y * 2 - 20,
                        -z * 2,
                        'grass' if z == 0 else 'dirt'
                    )

    def create_new_block(self, x, y, z, block_type=None):
        new_block_node = self.render.attachNewNode('new-block-placeholder')
        new_block_node.setPos(x, y, z)

        if block_type == 'grass':
            self.grass_block.instanceTo(new_block_node)
        elif block_type == 'dirt':
            self.dirt_block.instanceTo(new_block_node)
        elif block_type == 'sand':
            self.sand_block.instanceTo(new_block_node)
        elif block_type == 'stone':
            self.stone_block.instanceTo(new_block_node)
        elif block_type == 'slime':
            self.slime_block.instanceTo(new_block_node)

        block_solid = CollisionBox((-1, -1, -1), (1, 1, 1))
        block_node = CollisionNode('block-collision-node')
        block_node.addSolid(block_solid)
        collider = new_block_node.attachNewNode(block_node)
        collider.setPythonTag('owner', new_block_node)

    def load_models(self):
        self.grass_block = self.loader.loadModel('models/grass-block.glb')
        self.dirt_block = self.loader.loadModel('models/dirt-block.glb')
        self.stone_block = self.loader.loadModel('models/stone-block.glb')
        self.sand_block = self.loader.loadModel('models/sand-block.glb')
        self.slime_block = self.loader.loadModel('models/slime-block.glb')

    def setup_lights(self):
        main_light = DirectionalLight('main light')
        main_light_node_path = self.render.attachNewNode(main_light)
        main_light_node_path.setHpr(30, -60, 0)
        self.render.setLight(main_light_node_path)

        ambient_light = AmbientLight('ambient light')
        ambient_light.setColor((0.3, 0.3, 0.3, 1))
        ambient_light_node_path = self.render.attachNewNode(ambient_light)
        self.render.setLight(ambient_light_node_path)


game = MyGame()
game.run()
