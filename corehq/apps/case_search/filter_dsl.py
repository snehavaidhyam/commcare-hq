from __future__ import absolute_import, unicode_literals, print_function

from eulxml.xpath.ast import Step, serialize
from six import string_types, integer_types
from corehq.apps.es.case_search import case_property_text_query, case_property_range_query
from corehq.apps.es import filters


def print_ast(node):
    """Prints the AST provided by eulxml.xpath.parse

    Useful for debugging particular expressions
    """
    def visit(node, indent):
        print("\t" * indent, node)

        if hasattr(node, 'left'):
            indent += 1
            visit(node.left, indent)

        if hasattr(node, 'op'):
            print("\t" * indent, "##### {} #####".format(node.op))

        if hasattr(node, 'right'):
            visit(node.right, indent)
            indent -= 1

    visit(node, 0)


def build_filter_from_ast(node):
    """Builds an ES filter from an AST provided by eulxml.xpath.parse
    """

    OP_MAPPING = {
        'and': filters.AND,
        'not': filters.NOT,
        'or': filters.OR,
    }
    COMPARISON_MAPPING = {
        '>': 'gt',
        '>=': 'gte',
        '<': 'lt',
        '<=': 'lte',
    }

    def visit(node):
        if not hasattr(node, 'op'):
            raise ValueError("Malformed query")

        if node.op in ["=", "!="]:
            if isinstance(node.left, Step) and isinstance(node.right, integer_types + (string_types, float)):
                # This is a leaf
                # TODO: raise errors if something isn't right (e.g. if the RHS is another Step)
                q = case_property_text_query(serialize(node.left), node.right, '0')
                if node.op == '!=':
                    return filters.NOT(q)
                return q

        elif node.op in COMPARISON_MAPPING.keys():
            return case_property_range_query(serialize(node.left), **{COMPARISON_MAPPING[node.op]: node.right})

        elif node.op == '/':
            # a parent property lookup
            raise ValueError("Can't do parent property lookups directly, please transform the AST with the case_ids of the parents first")

        else:
            # This is another branch in the tree
            return OP_MAPPING[node.op](visit(node.left), visit(node.right))

    return visit(node)
