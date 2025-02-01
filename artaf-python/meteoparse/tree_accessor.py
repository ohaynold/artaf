"""This implements two convenience classes and a factory function to allow us to access Lark parse
trees in a more Pythonic way.
"""

import lark


class TreeAccessor:
    """
    Provide Pythonic access via properties and indexers to either a lark.Tree object or to an
    array of lark.Tree and/or lark.Token objects.
    x[item_name] will give a list of children of that name
    x.item_name will give the one child of that name and raise if there is not exactly one child
    :param item: either a lark.Tree object or to an array of lark.Tree and/or lark.Token objects
    :return: A wrapper around item that provides access via property calls, indexers, and len()
    """

    def __init__(self, item):
        if isinstance(item, lark.Tree):
            self.children = item.children
        else:
            self.children = item

    def __getattr__(self, item):
        """
        We use __getattr__ as a Pythonic way to access leave nodes that should exist exactly ones
        conveniently as if they were object properties.
        :param item: property name
        :return: property value, the unique element of the underlying data structure matching the
        name of item
        """
        candidates = self[item]
        if len(candidates) != 1:
            raise AttributeError("Expected to find exactly one selected child node.")
        return candidates[0]

    def __getitem__(self, item):
        """
        Select tree's children by integer index, slice, or name
        :param item: The selector
        :return: The selected children as a list
        """
        if isinstance(item, slice):
            return [self._decorate_child(a) for a in self.children[item]]
        if isinstance(item, int):
            return self._decorate_child(self.children[item])
        if isinstance(item, str):
            res = []
            for branch in self.children:
                if isinstance(branch, lark.Tree):
                    if branch.data == item:
                        res.append(TreeAccessor(branch))
                elif isinstance(branch, lark.Token):
                    if branch.type == item:
                        res.append(branch)
                else:
                    raise TypeError("Unexpected type hanging in our Lark tree.")
            return res
        raise IndexError("I don't know how to use this index.")

    def __len__(self):
        return len(self.children)

    @staticmethod
    def _decorate_child(item):
        """
        Decorate an object with a TreeAccessor if it is a Lark tree
        :param item: item to be decorated with an accessor
        :return: decorated item
        """
        if isinstance(item, lark.Tree):
            return TreeAccessor(item)
        return item
