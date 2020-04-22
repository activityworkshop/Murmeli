'''Manual test (not a discoverable unit test) for the Friendstorm'''

from PyQt5.QtWidgets import QApplication
from murmeli import brainstorm


def show_storm():
    '''Open a Qt window showing a basic, fixed storm'''
    app = QApplication([])

    bwin = brainstorm.StormWindow("Storm title")
    bwin.show()
    storm = brainstorm.Storm()
    storm.add_node(brainstorm.Node(None, "node1", "First node"))
    storm.add_node(brainstorm.Node(None, "node2", "Second node"))
    storm.add_node(brainstorm.Node(None, "node3", "Third node"))
    storm.add_node(brainstorm.Node(None, "node4", "Fourth node"))
    storm.add_edge("node1", "node2")
    storm.add_edge("node3", "node2")
    storm.add_edge("node4", "node2")
    storm.add_edge("node4", "node3")
    bwin.set_storm(storm)

    app.exec_()

if __name__ == '__main__':
    show_storm()
