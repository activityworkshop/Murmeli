'''Brainstorm application for concept-mapping
   Used as part of Murmeli for visualizing the contact graph
   All code copyright activityworkshop.net, see license.txt file'''

from PyQt5 import QtCore, QtGui, QtWidgets

class Edge(QtWidgets.QGraphicsItem):
    '''Class to represent a single edge in the graph'''

    def __init__(self, source_node, dest_node):
        '''Constructor giving the two nodes'''
        QtWidgets.QGraphicsItem.__init__(self)

        self.source_point = QtCore.QPointF()
        self.dest_point = QtCore.QPointF()
        self.setAcceptedMouseButtons(QtCore.Qt.RightButton)
        self.source = source_node
        self.dest = dest_node
        self.adjust()

    def set_source_node(self, node):
        '''Set the source node'''
        self.source = node
        self.adjust()

    def set_dest_node(self, node):
        '''Set the destination node'''
        self.dest = node
        self.adjust()

    def adjust(self):
        '''Adjust the edge with the given nodes'''
        if not self.source or not self.dest:
            return

        line = QtCore.QLineF(self.mapFromItem(self.source, self.source.boundingRect().center()),
                             self.mapFromItem(self.dest, self.dest.boundingRect().center()))
        if line.length() == 0.0:
            return

        self.prepareGeometryChange()
        self.source_point = line.p1()
        self.dest_point = line.p2()

    def boundingRect(self):
        '''Define rectangle enclosing the drawable area'''
        if not self.source or not self.dest:
            return QtCore.QRectF()
        extra = 5
        rect_size = QtCore.QSizeF(self.dest_point.x() - self.source_point.x(),
                                  self.dest_point.y() - self.source_point.y())
        rect = QtCore.QRectF(self.source_point, rect_size)
        return rect.normalized().adjusted(-extra, -extra, extra, extra)

    def shape(self):
        '''Define shape for mouse click detection'''
        path = QtGui.QPainterPath()
        path.moveTo(self.source_point)
        path.lineTo(self.dest_point)
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(10.0)
        return stroker.createStroke(path)

    def paint(self, painter, option, widget):
        '''Paint this edge'''
        if not self.source or not self.dest:
            return
        # Draw the line itself.
        line = QtCore.QLineF(self.source_point, self.dest_point)
        if line.length() == 0.0:
            return
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 1, QtCore.Qt.SolidLine,
                                  QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        painter.drawLine(line)


class Node(QtWidgets.QGraphicsTextItem):
    '''Class to represent a single node in the graph'''
    ATTRACTION_FACTOR = 0.25
    REPULSION_FACTOR = 2000
    REPULSION_RANGE = 500
    DRAG_FACTOR = 0.7
    LOW_VELOCITY = 2
    SMALLEST_VELOCITY = 0.2

    def __init__(self, graph_widget, nodeid, label):
        '''Constructor'''
        QtWidgets.QGraphicsTextItem.__init__(self, " " + (label or nodeid) + " ")
        self.graph = graph_widget
        self.label = label or nodeid
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)
        self.setPos(0.0, 0.0)
        self.velx = 0.0
        self.vely = 0.0
        self.rank = 0.0
        self.nodeid = nodeid
        self.setZValue(1)
        self.default_font_size = self.font().pointSize()
        self.num_edges = 0

    def calculate_repulsion(self, other):
        '''calculate repulsion between points'''
        other_center = self.mapFromItem(other, other.boundingRect().center())
        line = QtCore.QLineF(other_center, self.boundingRect().center())
        edgelen = line.length()
        if edgelen > 0 and edgelen < Node.REPULSION_RANGE:
            push = Node.REPULSION_FACTOR / edgelen / edgelen
            # if lines are horizontal, push them more (because names are horizontal)
            angle_factor = 1 + line.dx() * line.dx() / edgelen / edgelen * 2
            velx_inc = line.dx() * push * angle_factor
            vely_inc = line.dy() * push * angle_factor
            self.add_velocity(velx_inc, vely_inc)
            other.add_velocity(-velx_inc, -vely_inc)

    def calculate_attraction(self, other):
        '''calculate attraction between two points'''
        other_center = self.mapFromItem(other, other.boundingRect().center())
        line = QtCore.QLineF(other_center, self.boundingRect().center())
        if line.length() > 0:
            velx_inc = line.dx() * Node.ATTRACTION_FACTOR
            vely_inc = line.dy() * Node.ATTRACTION_FACTOR
            self.add_velocity(-velx_inc, -vely_inc)
            other.add_velocity(velx_inc, vely_inc)

    def add_velocity(self, x_inc, y_inc):
        '''Add the given velocity increments to our vector'''
        self.velx += x_inc
        self.vely += y_inc

    def advance(self):
        '''Advance the node'''
        if not self.scene() or self.scene().mouseGrabberItem() is self:
            self.velx = self.vely = 0.0
            return False
        # slow things down
        self.velx *= Node.DRAG_FACTOR
        self.vely *= Node.DRAG_FACTOR
        # slow down the slow things more
        if abs(self.velx) < Node.LOW_VELOCITY:
            self.velx *= 0.95
        if abs(self.vely) < Node.LOW_VELOCITY:
            self.vely *= 0.95
        if abs(self.velx) < Node.SMALLEST_VELOCITY and abs(self.vely) < Node.SMALLEST_VELOCITY:
            self.velx = self.vely = 0.0
            return False
        # Use velx, vely to calculate new position
        scene_rect = self.scene().sceneRect()
        new_pos = self.pos() + QtCore.QPointF(self.velx, self.vely)
        new_pos.setX(min(max(new_pos.x(), scene_rect.left() + 10), scene_rect.right() - 10))
        new_pos.setY(min(max(new_pos.y(), scene_rect.top() + 10), scene_rect.bottom() - 10))
        self.setPos(new_pos)
        return True

    def update_rank(self):
        '''Update the rank of this node and change the appearance accordingly'''
        self.rank = self.nextrank
        font = self.font()
        font.setBold(self.rank > 1.2)
        if self.rank < 0.9:
            font.setPointSize(self.default_font_size - 3)
        elif self.rank > 1.25:
            font.setPointSize(self.default_font_size + 3)
        else:
            font.setPointSize(self.default_font_size)
        self.setFont(font)

    def paint(self, painter, option, widget):
        '''Paint this node'''
        painter.setBrush(QtCore.Qt.white)
        painter.drawEllipse(self.boundingRect())
        QtWidgets.QGraphicsTextItem.paint(self, painter, option, widget)

    def shape(self):
        '''Define shape for mouse click detection'''
        path = QtGui.QPainterPath()
        path.addEllipse(self.boundingRect())
        return path

    def itemChange(self, change, value):
        '''Override parent method to respond to items being moved'''
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            if self.graph != None:
                self.graph.itemMoved()
        return QtWidgets.QGraphicsItem.itemChange(self, change, value)

    def mousePressEvent(self, event):
        '''override the mouse event handling to pass unprocessed events upwards'''
        QtWidgets.QGraphicsTextItem.mousePressEvent(self, event)
        if event.button() == QtCore.Qt.RightButton:
            print("Mouse pressed on Node '%s'" % self.label)


class Storm:
    '''Class to hold a set of nodes and their connections'''
    def __init__(self):
        self.title = ""
        self.author = ""
        self.nodes = []
        self.edges = []
        self.nodedict = {}

    def add_node(self, node):
        '''Add the given node to the storm, if it's not there already'''
        if not self.has_node(node.nodeid):
            self.nodedict[node.nodeid] = node
            self.nodes.append(node)

    def add_edge(self, sourceid, destid):
        '''Add an edge between two nodes'''
        source_node = self.nodedict.get(sourceid)
        dest_node = self.nodedict.get(destid)
        if source_node is None or dest_node is None:
            print("Can't find nodes for edge", sourceid, "-", destid)
        elif source_node != dest_node:
            for edge in self.edges:
                if (edge.source.nodeid == sourceid and edge.dest.nodeid == destid) or \
                 (edge.dest.nodeid == sourceid and edge.source.nodeid == destid):
                    # edge already exists
                    return
            edge = Edge(source_node, dest_node)
            self.edges.append(edge)

    def get_num_nodes(self):
        '''Return the number of nodes'''
        return len(self.nodes)

    def get_num_edges(self):
        '''Return the number of edges'''
        return len(self.edges)

    def has_node(self, nodeid):
        '''Check whether the given nodeid is already present or not'''
        return True if self.nodedict.get(nodeid) else False

    def get_label(self, nodeid):
        '''Get the label corresponding to the given node id'''
        node = self.nodedict.get(nodeid)
        return node.label if node else None
