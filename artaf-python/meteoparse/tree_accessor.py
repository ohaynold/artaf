# noinspection GrazieInspection
"""This implements two convenience classes and a factory function to allow us to access Lark parse
trees in a more Pythonic way.

The intended way to construct these is with lark_tree_accessor and a lark.Tree or an array of Lark
tree elements as its argument.
"""

import lark


class AbstractTreeAccessor:
    """
    Children of these class are meant to access a lark.Tree in a more convenient and Pythonic format.
    x[property_name] will give a list of all branches or leaves matching property_name
    x.property_name will give the exactly one branch or leaf that matches and throw otherwise
    """

    def __getattr__(self, item):
        # noinspection GrazieInspection
        """
        We use __getattr__ as a Pythonic way to access leave nodes that should exist exactly ones conveniently
        as if they were object properties.
        :param item: property name
        :return: property value, the exactly element of the underlying data structure matching the name of item
        """
        candidates = self[item]
        if len(candidates) != 1:
            raise AttributeError("Expected to find exactly one selected child node.")
        return candidates[0]


class TreeAccessor(AbstractTreeAccessor):
    """
    Convenience accessor for lark.Tree. Instantiate via lark_tree_accessor()
    """

    def __init__(self, tree):
        self.tree = tree

    def __getitem__(self, item):
        if isinstance(item, slice):
            res = []
            for a in self.tree.children[item]:
                if isinstance(a, lark.Tree):
                    res.append(TreeAccessor(a))
                else:
                    res.append(a)
            return res
        elif isinstance(item, int):
            res = self.tree.children[item]
            if isinstance(res, lark.Tree):
                return TreeAccessor(res)
            else:
                return res
        elif isinstance(item, str):
            res = []
            for child in self.tree.children:
                if isinstance(child, lark.Tree):
                    if child.data == item:
                        res.append(TreeAccessor(child))
                elif isinstance(child, lark.Token):
                    if child.type == item:
                        res.append(child)
                else:
                    raise TypeError("Unexpected type hanging in our Lark tree.")
            return res
        else:
            raise IndexError("I don't know how to use this index.")

    def __len__(self):
        return len(self.tree.children)


class BranchesAccessor(AbstractTreeAccessor):
    """
    Convenience accessor for [lark.Tree|lark.Token]. Instantiate via lark_tree_accessor()
    """

    def __init__(self, branches):
        self.branches = branches

    def __getitem__(self, item):
        if isinstance(item, slice) or isinstance(item, int):
            return self.branches[item]
        elif isinstance(item, str):
            res = []
            for child in self.branches:
                if isinstance(child, lark.Tree):
                    if child.data == item:
                        res.append(TreeAccessor(child))
                elif isinstance(child, lark.Token):
                    if child.type == item:
                        res.append(child)
                else:
                    raise TypeError("Unexpected type hanging in our Lark tree.")
            return res
        else:
            raise IndexError("I don't know how to use this index.")

    def __len__(self):
        return len(self.branches)


def lark_tree_accessor(item):
    """
    Provide Pythonic access via properties and indexers to either a lark.Tree object or to an
    array of lark.Tree and/or lark.Token objects.
    :param item: either a lark.Tree object or to an array of lark.Tree and/or lark.Token objects
    :return: A wrapper around item that provides access via property calls, indexers, and len()
    """
    if isinstance(item, lark.Tree):
        return TreeAccessor(item)
    elif isinstance(item, list):
        return BranchesAccessor(item)
    else:
        raise TypeError("Unexpected type hanging in our Lark tree.")
