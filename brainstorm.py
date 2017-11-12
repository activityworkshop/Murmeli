'''Brainstorm-derived code for showing Murmeli's contact graph'''

import math
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QMainWindow, QGraphicsView, QGraphicsScene
from brainstormdata import Node, Edge, Storm


class GraphWidget(QGraphicsView):
	'''Class for the GraphWidget in the middle of the gui'''
	def __init__(self):
		'''Constructor'''
		QGraphicsView.__init__(self)

		self.timerId = 0
		self.drawing = False

		scene = Scene(self)
		scene.setItemIndexMethod(QGraphicsScene.NoIndex)
		scene.setSceneRect(-350, -250, 700, 500)
		self.setScene(scene)
		self.setCacheMode(QGraphicsView.CacheBackground)
		self.setRenderHint(QtGui.QPainter.Antialiasing)
		self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
		self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

		self.storm = None
		self.scale(0.8, 0.8)
		self.setMinimumSize(400, 400)

	def replaceScene(self, storm):
		'''Replace the current scene with the given Storm object'''
		self.storm = storm
		scene = self.scene()
		scene.clear()
		shouldrandomize = True
		for node in storm.nodes:
			node.graph = self
			scene.addItem(node)
			if node.pos().x() != 0 or node.pos().y() != 0:
				shouldrandomize = False
		for edge in storm.edges:
			scene.addItem(edge)
		# only randomize positions if they're all 0 (respect loaded positions)
		if shouldrandomize:
			self.randomizeNodePositions()
		self.calculateRanks()

	def updateScene(self, storm):
		# add unknown nodes, edges
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
		self.calculateRanks()
		self.itemMoved()

	def itemMoved(self):
		if self.timerId == 0:
			self.timerId = self.startTimer(1000 / 25) # 25fps

	def keyPressEvent(self, event):
		'''Respond to a keypress (for zoom and randomize)'''
		key = event.key()

		if key == QtCore.Qt.Key_Plus:
			self.scaleView(1.2)
		elif key == QtCore.Qt.Key_Minus:
			self.scaleView(1 / 1.2)
		elif key == QtCore.Qt.Key_Space or key == QtCore.Qt.Key_Enter:
			self.randomizeNodePositions()
		else:
			QtGui.QGraphicsView.keyPressEvent(self, event)

	def randomizeNodePositions(self):
		'''If the nodes get stuck in the wrong positions, we can randomize them'''
		for item in list(self.scene().items()):
			if isinstance(item, Node):
				item.setPos(-150 + QtCore.qrand() % 300, -150 + QtCore.qrand() % 300)

	def calculateRanks(self):
		'''Calculate the rank of each node iteratively'''
		nodes = [item for item in list(self.scene().items()) if isinstance(item, Node)]
		edges = [item for item in list(self.scene().items()) if isinstance(item, Edge)]
		# initialize with all ranks 1
		for node in nodes:
			node.rank = 1
			node.numEdges = 0
		for edge in edges:
			edge.source.numEdges += 1
			edge.dest.numEdges += 1
		DAMPING_FACTOR = 0.85
		keepGoing = True
		numLoops = 0
		while keepGoing and numLoops < 20:
			# reset nextrank for all nodes
			for node in nodes:
				node.nextrank = (1 - DAMPING_FACTOR)
			# feed rank through all edges
			for edge in edges:
				edge.source.nextrank += DAMPING_FACTOR * edge.dest.rank / edge.dest.numEdges
				edge.dest.nextrank += DAMPING_FACTOR * edge.source.rank / edge.source.numEdges
			# update all ranks
			keepGoing = False
			for node in nodes:
				if abs(node.rank - node.nextrank) > 0.01:
					keepGoing = True
				node.updateRank()
			numLoops += 1

	def timerEvent(self, event):
		'''Called by timer events, to update the positions and redraw'''
		if self.drawing: return
		self.drawing = True
		nodes = [item for item in list(self.scene().items()) if isinstance(item, Node)]
		edges = [item for item in list(self.scene().items()) if isinstance(item, Edge)]

		# attraction between two connected nodes
		for edge in edges:
			edge.source.calculateAttraction(edge.dest)

		# repulsion between every pair of nodes
		node1num = 0
		for n1, node1 in enumerate(nodes):
			node1num += 1
			node2num = 0
			for n2, node2 in enumerate(nodes):
				node2num += 1
				if n2 > n1:
					node1.calculateRepulsion(node2)

		itemsMoved = False
		for node in nodes:
			if node.advance():
				itemsMoved = True

		for edge in edges:
			edge.adjust()

		if not itemsMoved:
			self.killTimer(self.timerId)
			self.timerId = 0
		self.drawing = False

	def wheelEvent(self, event):
		'''Respond to wheel events, to zoom view'''
		self.scaleView(math.pow(2.0, -event.delta() / 240.0))

	def scaleView(self, scaleFactor):
		'''Zoom view by the given scale factor'''
		factor = self.matrix().scale(scaleFactor, scaleFactor).mapRect(QtCore.QRectF(0, 0, 1, 1)).width()
		if factor < 0.07 or factor > 100:
			return
		self.scale(scaleFactor, scaleFactor)


class Scene(QGraphicsScene):
	'''Subclass for graphics scene'''
	def __init__(self, parent):
		QGraphicsScene.__init__(self, parent)

	# override the mouse event handling to pass unprocessed events upwards
	def mousePressEvent(self, event):
		QGraphicsScene.mousePressEvent(self, event)
		if event.button() == QtCore.Qt.RightButton and not event.isAccepted():
			self.parent().storm.processRightClick(event, self)


class Brainstorm(QMainWindow):
	'''Main window class for Brainstorm'''

	def __init__(self, windowTitle=None):
		'''Constructor'''
		QMainWindow.__init__(self)
		self._setupUi(windowTitle)
		self.storm = None
		self.setStorm(Storm())

	def setStorm(self, storm):
		'''Set the current storm and its callback functions'''
		self.storm = storm
		if storm is not None:
			self.gwidget.replaceScene(self.storm)

	def _setupUi(self, windowTitle):
		'''Initialise the user interface'''
		self.setObjectName("MainWindow")
		self.resize(551, 343)
		self.gwidget = GraphWidget()
		self.setCentralWidget(self.gwidget)
		self.statusbar = QtGui.QStatusBar(self)
		self.statusbar.setObjectName("statusbar")
		self.setStatusBar(self.statusbar)
		# texts
		self.setWindowTitle("Murmeli" if windowTitle is None else windowTitle)
		self.setStatusTip("")

	def updateScene(self):
		self.gwidget.updateScene(self.storm)
