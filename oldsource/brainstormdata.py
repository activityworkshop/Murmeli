'''Brainstorm application for concept-mapping
   Used as part of Murmeli for visualizing the contact graph
   All code copyright activityworkshop.net, see license.txt file'''

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsTextItem

class Edge(QGraphicsItem):
	'''Class to represent a single edge in the graph'''

	def __init__(self, sourceNode, destNode):
		'''Constructor giving the two nodes'''
		QGraphicsItem.__init__(self)

		self.sourcePoint = QtCore.QPointF()
		self.destPoint = QtCore.QPointF()
		self.setAcceptedMouseButtons(QtCore.Qt.RightButton)
		self.source = sourceNode
		self.dest = destNode
		self.adjust()

	def sourceNode(self):
		return self.source

	def setSourceNode(self, node):
		self.source = node
		self.adjust()

	def destNode(self):
		return self.dest

	def setDestNode(self, node):
		self.dest = node
		self.adjust()

	def adjust(self):
		if not self.source or not self.dest:
			return

		line = QtCore.QLineF(self.mapFromItem(self.source, self.source.boundingRect().center()),
			self.mapFromItem(self.dest, self.dest.boundingRect().center()))
		if line.length() == 0.0:
			return

		self.prepareGeometryChange()
		self.sourcePoint = line.p1()
		self.destPoint = line.p2()

	def boundingRect(self):
		'''Define rectangle enclosing the drawable area'''
		if not self.source or not self.dest:
			return QtCore.QRectF()
		extra = 5
		return QtCore.QRectF(self.sourcePoint,
			QtCore.QSizeF(self.destPoint.x() - self.sourcePoint.x(),
			self.destPoint.y() - self.sourcePoint.y())).normalized().adjusted(-extra, -extra, extra, extra)

	def shape(self):
		'''Define shape for mouse click detection'''
		path = QtGui.QPainterPath()
		path.moveTo(self.sourcePoint)
		path.lineTo(self.destPoint)
		stroker = QtGui.QPainterPathStroker()
		stroker.setWidth(10.0)
		return stroker.createStroke(path)

	def paint(self, painter, option, widget):
		if not self.source or not self.dest:
			return
		# Draw the line itself.
		line = QtCore.QLineF(self.sourcePoint, self.destPoint)
		if line.length() == 0.0:
			return
		painter.setPen(QtGui.QPen(QtCore.Qt.black, 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
		painter.drawLine(line)


class Node(QGraphicsTextItem):
	'''Class to represent a single node in the graph'''
	ATTRACTION_FACTOR = 0.25
	REPULSION_FACTOR = 1800
	REPULSION_RANGE = 500
	DRAG_FACTOR = 0.7
	LOW_VELOCITY = 2
	SMALLEST_VELOCITY = 0.2

	def __init__(self, graphWidget, nodeid, label, x=0, y=0):
		'''Constructor'''
		QGraphicsTextItem.__init__(self, " " + label + " ")
		self.graph = graphWidget
		self.label = label
		self.setFlag(QGraphicsItem.ItemIsMovable)
		try:
			self.setFlag(QGraphicsItem.ItemSendsGeometryChanges) # required from version 4.6
		except: pass # version 4.5 throws error
		self.setPos(float(x), float(y))
		self.velx = 0.0
		self.vely = 0.0
		self.rank = 0.0
		self.nodeid = nodeid
		self.setZValue(1)
		self.defaultPointSize = self.font().pointSize()
		self.numEdges = 0

	def calculateRepulsion(self, other):
		'''calculate distance between points'''
		line = QtCore.QLineF(self.mapFromItem(other, other.boundingRect().center()), self.boundingRect().center())
		edgelen = line.length()
		if edgelen > 0 and edgelen < Node.REPULSION_RANGE:
			push = Node.REPULSION_FACTOR / edgelen / edgelen
			velxIncrement = line.dx() * push
			velyIncrement = line.dy() * push
			self.addVelocity(velxIncrement, velyIncrement)
			other.addVelocity(-velxIncrement, -velyIncrement)

	def calculateAttraction(self, other):
		'''calculate distance between two points'''
		line = QtCore.QLineF(self.mapFromItem(other, other.boundingRect().center()), self.boundingRect().center())
		if line.length() > 0:
			velxIncrement = line.dx() * Node.ATTRACTION_FACTOR
			velyIncrement = line.dy() * Node.ATTRACTION_FACTOR
			self.addVelocity(-velxIncrement, -velyIncrement)
			other.addVelocity(velxIncrement, velyIncrement)

	def addVelocity(self, xInc, yInc):
		self.velx += xInc
		self.vely += yInc

	def advance(self):
		if not self.scene() or self.scene().mouseGrabberItem() is self:
			self.velx = self.vely = 0.0
			return False
		# slow things down
		self.velx *= Node.DRAG_FACTOR
		self.vely *= Node.DRAG_FACTOR
		# slow down the slow things more
		if abs(self.velx) < Node.LOW_VELOCITY: self.velx *= 0.95
		if abs(self.vely) < Node.LOW_VELOCITY: self.vely *= 0.95
		if abs(self.velx) < Node.SMALLEST_VELOCITY and abs(self.vely) < Node.SMALLEST_VELOCITY:
			self.velx = self.vely = 0.0
			return False
		# Use velx, vely to calculate new position
		sceneRect = self.scene().sceneRect()
		newPos = self.pos() + QtCore.QPointF(self.velx, self.vely)
		newPos.setX(min(max(newPos.x(), sceneRect.left() + 10), sceneRect.right() - 10))
		newPos.setY(min(max(newPos.y(), sceneRect.top() + 10), sceneRect.bottom() - 10))
		self.setPos(newPos)
		return True

	def updateRank(self):
		'''Update the rank of this node and change the appearance accordingly'''
		self.rank = self.nextrank
		font = self.font()
		font.setBold(self.rank > 1.2)
		if self.rank < 0.9:
			font.setPointSize(self.defaultPointSize - 3)
		elif self.rank > 1.25:
			font.setPointSize(self.defaultPointSize + 3)
		else:
			font.setPointSize(self.defaultPointSize)
		self.setFont(font)

	def paint(self, painter, option, widget):
		painter.setBrush(QtCore.Qt.white)
		painter.drawEllipse(self.boundingRect())
		QGraphicsTextItem.paint(self, painter, option, widget)

	def shape(self):
		'''Define shape for mouse click detection'''
		path = QtGui.QPainterPath()
		path.addEllipse(self.boundingRect())
		return path

	def itemChange(self, change, value):
		if change == QGraphicsItem.ItemPositionChange:
			if self.graph != None:
				self.graph.itemMoved()
		return QGraphicsItem.itemChange(self, change, value)


class Storm:
	'''Class to hold a set of nodes and their connections'''
	def __init__(self):
		self.title = ""
		self.author = ""
		self.nodes = []
		self.edges = []
		self.nodedict = {}
		self.connectFromNode = None

	def addNode(self, node):
		'''Add the given node to the storm'''
		if self.nodedict.get(node.nodeid):
			print("node ", node.nodeid, "already exists")
		else:
			self.nodedict[node.nodeid] = node
			self.nodes.append(node)
		self.connectFromNode = None

	def addEdge(self, sourceid, destid):
		'''Add an edge between two nodes'''
		sourceNode = self.nodedict.get(sourceid)
		destNode = self.nodedict.get(destid)
		if sourceNode is None or destNode is None:
			print("Can't find nodes for edge", sourceid, "-", destid)
		elif sourceNode != destNode:
			for edge in self.edges:
				if (edge.source.nodeid == sourceid and edge.dest.nodeid == destid) or \
				 (edge.dest.nodeid == sourceid and edge.source.nodeid == destid):
					print("edge already exists")
					return
			edge = Edge(sourceNode, destNode)
			self.edges.append(edge)
		self.connectFromNode = None

	def getUnusedNodeId(self):
		'''Get the next unused node id for a new node'''
		nodenum = len(self.nodes) + 1
		while self.nodedict.get("node" + str(nodenum)):
			nodenum += 1
		return "node" + str(nodenum)

	def deleteNode(self, node):
		'''Remove the specified node from the storm, and its edges (not needed for Murmeli?)'''
		if self.nodedict.get(node.nodeid):
			del self.nodedict[node.nodeid]
			self.nodes.remove(node)
			# also remove all connected edges
			newedges = []
			for edge in self.edges:
				if edge.source != node and edge.dest != node:
					newedges.append(edge)
			self.edges = newedges
		self.connectFromNode = None

	def deleteEdge(self, edge):
		'''Delete a single edge from the storm (not needed for Murmeli?)'''
		self.edges.remove(edge)
		self.connectFromNode = None

	def createConnectionFrom(self, node):
		self.connectFromNode = node

	def updateScene(self):
		self.updateCallback()
