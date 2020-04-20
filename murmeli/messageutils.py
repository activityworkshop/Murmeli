'''Module for building message trees'''

class MessageLeaf:
    '''Leaf of a message tree, including single message and its siblings
       (which are also MessageLeafs)'''

    def __init__(self, msg):
        '''Constructor giving message object'''
        self.msg = msg
        self.level = 0
        self.children = []
        self.has_parent = False

    def add_child(self, child):
        '''Add a child to the leaf'''
        self.children.append(child)
        child.has_parent = True

    def get_max_level(self):
        '''Find the minimum level of this message based on its children'''
        max_level = -1
        for child in self.children:
            child_level = child.get_max_level()
            if child_level > max_level:
                max_level = child_level
        return max_level + 1

    def set_level(self, level):
        '''Set the actual level of this message'''
        self.level = level
        for child in self.children:
            child.set_level(level-1)

    def add_to_list(self, result_list):
        '''Add this leaf and all its children recursively to the given list'''
        for child in self.children:
            child.add_to_list(result_list)
        result_list.append(self)


class MessageTree:
    '''Holds a tree of MessageLeaf objects'''
    def __init__(self):
        self.msg_list = []
        self.msgs_by_hash = {}

    def add_msg(self, msg):
        '''Adds a message to the tree'''
        leaf = MessageLeaf(msg)
        child_index = self._index_of_first_child(msg.get('messageHash'))
        if child_index >= 0:
            self.msg_list.insert(child_index, leaf)
        else:
            self.msg_list.append(leaf)
        self.msgs_by_hash[msg['messageHash']] = leaf

    def build(self):
        '''Now that all leafs have been collected, build the tree and calculate the levels'''
        # Loop to connect children to parents
        for leaf in self.msg_list:
            parent_id = leaf.msg.get("parentHash")
            parent_leaf = self.msgs_by_hash.get(parent_id) if parent_id else None
            if parent_leaf:
                parent_leaf.add_child(leaf)
        # Loop to get and set levels
        result_list = []
        for leaf in self.msg_list:
            if not leaf.has_parent:
                root_level = leaf.get_max_level()
                leaf.set_level(root_level)
                leaf.add_to_list(result_list)
        return result_list

    def _index_of_first_child(self, parent_hash):
        '''Look through the list of messages for one whose parent has the given hash
           and return its index.  Returns -1 if not found.'''
        if parent_hash:
            for index, leaf in enumerate(self.msg_list):
                if leaf.msg.get('parentHash') == parent_hash:
                    return index
        return -1
