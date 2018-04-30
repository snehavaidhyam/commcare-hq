from __future__ import absolute_import, print_function, unicode_literals

from eulxml.xpath.ast import Step, serialize
from six import integer_types, string_types

from corehq.apps.es import filters
from corehq.apps.es.case_search import (
    CaseSearchES,
    case_property_range_query,
    exact_case_property_text_query,
    related_case_query,
)


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

    def parent_property_lookup(node):
        """given a node of the form `parent/foo = 'thing'`, all case_ids where `foo = thing`
        """
        prop = serialize(node.left.right)
        value = node.right
        return CaseSearchES().case_property_query(prop, value).scroll_ids()  # TODO: domain

    def child_case_lookup(case_ids, identifier):
        """returns a list of all case_ids who have parents `case_id` with the relationship `identifier`
        """
        return CaseSearchES().get_child_cases(case_ids, identifier).scroll_ids()

    def _is_related_case_lookup(node):
        """Returns whether a particular AST node is a related case lookup

        e.g. `parent/host/thing = 'foo'`
        """
        return hasattr(node, 'left') and hasattr(node.left, 'op') and node.left.op == '/'

    def visit(node):
        if not hasattr(node, 'op'):
            raise ValueError("Malformed query")

        if _is_related_case_lookup(node):
            # related doc lookup
            ids = parent_property_lookup(node)  # the ids of the highest level cases that match the case_property

            # walk down the tree and select all child cases
            n = node.left
            final_identifier = serialize(n.left)
            related_case_lookups = []
            while _is_related_case_lookup(n):
                # find the top level, then walk down
                n = n.left
                related_case_lookups.append(n)

            if related_case_lookups:
                final_identifier = serialize(related_case_lookups[0].right)
                for n in reversed(related_case_lookups):
                    # Performs a "join" to find related cases
                    # does one lookup per ancestory level
                    ids = child_case_lookup(ids, identifier=serialize(n.left))
                    if not ids:
                        break
            return related_case_query(ids, final_identifier)

        if node.op in ["=", "!="]:
            if isinstance(node.left, Step) and isinstance(node.right, integer_types + (string_types, float)):
                # This is a leaf
                # TODO: raise errors if something isn't right (e.g. if the RHS is another Step)
                q = exact_case_property_text_query(serialize(node.left), node.right)
                if node.op == '!=':
                    return filters.NOT(q)
                return q

        if node.op in COMPARISON_MAPPING.keys():
            return case_property_range_query(serialize(node.left), **{COMPARISON_MAPPING[node.op]: node.right})

        # This is another branch in the tree
        return OP_MAPPING[node.op](visit(node.left), visit(node.right))

    return visit(node)
