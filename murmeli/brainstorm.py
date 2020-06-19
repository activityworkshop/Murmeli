'''Brainstorm-derived code for showing Murmeli's contact graph'''

import math
from PyQt5 import QtCore, QtGui, QtWidgets
from murmeli.brainstormdata import Node, Edge, Storm


class GraphWidget(QtWidgets.QGraphicsView):
    '''Class for the GraphWidget in the middle of the gui'''
    def __init__(self):
        '''Constructor'''
        QtWidgets.QGraphicsView.__init__(self)

        self.timer_id = 0
        self.drawing = False

        scene = QtWidgets.QGraphicsScene(self)
        scene.setItemIndexMethod(QtWidgets.QGraphicsScene.NoIndex)
        scene.setSceneRect(-350, -250, 700, 500)
        self.setScene(scene)
        self.setCacheMode(QtWidgets.QGraphicsView.CacheBackground)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)

        self.storm = None
        self.scaleView(0.8)
        self.setMinimumSize(400, 400)

    def replaceScene(self, storm):
        '''Replace the current scene with the given Storm object'''
        self.storm = storm
        scene = self.scene()
        scene.clear()
        should_randomize = True
        for node in storm.nodes:
            node.graph = self
            scene.addItem(node)
            if node.pos().x() != 0 or node.pos().y() != 0:
                should_randomize = False
        for edge in storm.edges:
            scene.addItem(edge)
        # only randomize positions if they're all 0 (respect loaded positions)
        if should_randomize:
            self.randomize_positions()
        self.calculate_ranks()

    def updateScene(self, storm):
        '''add unknown nodes, edges'''
        for node in storm.nodes:
            if node not in list(self.scene().items()):
                node.graph = self
                self.scene().addItem(node)
        for edge in storm.edges:
            if edge not in list(self.scene().items()):
                self.scene().addItem(edge)
        # need to subtract unwanted items too
        itemstodelete = []
        for item in list(self.scene().items()):
            if item not in storm.nodes and item not in storm.edges:
                itemstodelete.append(item)
        for item in itemstodelete:
            self.scene().removeItem(item)
        self.calculate_ranks()
        self.itemMoved()

    def itemMoved(self):
        '''Start an animation timer if an object has been moved'''
        if self.timer_id == 0:
            self.timer_id = self.startTimer(1000 / 25) # 25fps

    def keyPressEvent(self, event):
        '''Respond to a keypress (for zoom and randomize)'''
        key = event.key()

        if key == QtCore.Qt.Key_Plus:
            self.scaleView(1.2)
        elif key == QtCore.Qt.Key_Minus:
            self.scaleView(1 / 1.2)
        elif key == QtCore.Qt.Key_Space or key == QtCore.Qt.Key_Enter:
            self.randomize_positions()
        else:
            QtWidgets.QGraphicsView.keyPressEvent(self, event)

    def randomize_positions(self):
        '''If the nodes get stuck in the wrong positions, we can randomize them'''
        for item in list(self.scene().items()):
            if isinstance(item, Node):
                item.setPos(-150 + QtCore.qrand() % 300, -150 + QtCore.qrand() % 300)

    def calculate_ranks(self):
        '''Calculate the rank of each node iteratively'''
        nodes = [item for item in list(self.scene().items()) if isinstance(item, Node)]
        edges = [item for item in list(self.scene().items()) if isinstance(item, Edge)]
        # initialize with all ranks 1
        for node in nodes:
            node.rank = 1
            node.numEdges = 0
        for edge in edges:
            edge.source.num_edges += 1
            edge.dest.num_edges += 1
        DAMPING_FACTOR = 0.85
        keep_going = True
        num_loops = 0
        while keep_going and num_loops < 20:
            # reset nextrank for all nodes
            for node in nodes:
                node.nextrank = (1 - DAMPING_FACTOR)
            # feed rank through all edges
            for edge in edges:
                edge.source.nextrank += DAMPING_FACTOR * edge.dest.rank / edge.dest.num_edges
                edge.dest.nextrank += DAMPING_FACTOR * edge.source.rank / edge.source.num_edges
            # update all ranks
            keep_going = False
            for node in nodes:
                if abs(node.rank - node.nextrank) > 0.01:
                    keep_going = True
                node.update_rank()
            num_loops += 1

    def timerEvent(self, _):
        '''Called by timer events, to update the positions and redraw'''
        if self.drawing:
            return
        self.drawing = True
        nodes = [item for item in list(self.scene().items()) if isinstance(item, Node)]
        edges = [item for item in list(self.scene().items()) if isinstance(item, Edge)]

        # attraction between two connected nodes
        for edge in edges:
            edge.source.calculate_attraction(edge.dest)

        # repulsion between every pair of nodes
        node1num = 0
        for ni1, node1 in enumerate(nodes):
            node1num += 1
            node2num = 0
            for ni2, node2 in enumerate(nodes):
                node2num += 1
                if ni2 > ni1:
                    node1.calculate_repulsion(node2)

        items_moved = False
        for node in nodes:
            if node.advance():
                items_moved = True

        for edge in edges:
            edge.adjust()

        if not items_moved:
            self.killTimer(self.timer_id)
            self.timer_id = 0
        self.drawing = False

    def wheelEvent(self, event):
        '''Respond to wheel events, to zoom view'''
        self.scaleView(math.pow(2.0, -event.delta() / 240.0))

    def scaleView(self, scale_factor):
        '''Zoom view by the given scale factor'''
        self.scale(scale_factor, scale_factor)


class StormWindow(QtWidgets.QMainWindow):
    '''Main window class for friend storm'''

    def __init__(self, window_title=None):
        '''Constructor'''
        QtWidgets.QMainWindow.__init__(self)
        self._setup_ui(window_title)
        self.storm = None

    def set_storm(self, storm):
        '''Set the current storm and its callback functions'''
        self.storm = storm
        if storm:
            self.gwidget.replaceScene(self.storm)

    def _setup_ui(self, window_title):
        '''Initialise the user interface'''
        self.setObjectName("MainWindow")
        self.resize(600, 450)
        self.gwidget = GraphWidget()
        self.setCentralWidget(self.gwidget)
        # self.statusbar = QtGui.QStatusBar(self)
        # self.statusbar.setObjectName("statusbar")
        # self.setStatusBar(self.statusbar)
        # texts
        self.setWindowTitle(window_title or "Murmeli")
        # self.setStatusTip("")

    def updateScene(self):
        '''Pass on the update request to the widget'''
        self.gwidget.updateScene(self.storm)


class FriendStorm(Storm):
    '''A specific kind of Storm for adding friends'''
    def __init__(self, own_id, own_name):
        Storm.__init__(self)
        self.own_id = own_id
        self.add_node(Node(None, own_id, own_name))

    def add_friend(self, friend_id, friend_name):
        '''Add a friend of mine to the storm'''
        assert friend_id
        self.add_node(Node(None, friend_id, friend_name))
        self.add_edge(self.own_id, friend_id)

    def connect_friends(self, friend1_id, friend2_id):
        '''Connect the two friends of ours together'''
        self.add_edge(friend1_id, friend2_id)

    def add_friends_friend(self, my_friend_id, their_friend_id, friend_name):
        '''Add a friend of my friend to the storm'''
        assert my_friend_id
        assert their_friend_id
        assert self.has_node(my_friend_id)
        self.add_node(Node(None, their_friend_id, friend_name or their_friend_id))
        self.add_edge(my_friend_id, their_friend_id)
