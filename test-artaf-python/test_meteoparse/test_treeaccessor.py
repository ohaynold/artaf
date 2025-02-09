"""Tests for Tree Accessor. Not much, since most testing gets covered by TAF parse test cases"""
import pytest
from lark import Token, Tree

from meteoparse.tree_accessor import TreeAccessor


class TestTreeAccessor:
    """Tests for Tree Accessor. Not much, since most testing gets covered by TAF parse test
    cases. So here we only cover what's not already exercised by the TAF parse test cases,
    which exercise the functionality in its proper context."""

    def test_slice_access(self):
        """Check access to tree with slices"""
        accessor = TreeAccessor([Token("Token1", 1), Token("Token2", 2), Token("Token3", 3)])
        selected_slice = accessor[:2]
        values = [x.value for x in selected_slice]
        assert values == [1, 2]

    def test_unexpected_item(self):
        """Check that unexpected item in tree raises"""
        accessor = TreeAccessor([Token("Token1", 1), Token("Token2", 2), 3])
        with pytest.raises(TypeError):
            accessor.Token1  # pylint: disable=pointless-statement

    def test_unexpected_index(self):
        """Check that unexpected index type raises"""
        accessor = TreeAccessor([Token("Token1", 1), Token("Token2", 2), 3])
        with pytest.raises(IndexError):
            accessor[3.14]  # pylint: disable=pointless-statement

    def test_decorate_child(self):
        """Check that children are properly decorated as TreeAccessors"""
        accessor = TreeAccessor([Tree("tree1", []), Tree("tree2", [])])
        subtree = accessor[0]
        assert isinstance(subtree, TreeAccessor)
