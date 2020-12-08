from pprint import pprint

import radb
import radb.ast
import radb.parse

dd = {"Person": {"name": "string", "age": "integer", "gender": "string"}, "Eats": {"name": "string", "pizza": "string"}}
stmt = "\select_{E.pizza = 'mushroom' and E.price < 10} \\rename_{E: *}(Eats);"
stmt_result = "\select_{E.pizza = 'mushroom'} \select_{E.price < 10} \\rename_{E: *}(Eats);"
ra = radb.parse.one_statement_from_string(stmt)
ra_result = radb.parse.one_statement_from_string(stmt_result)
# print(ra)
# print(ra_result)
# print('yup1')


def break_select(ra):
    """ Breaks up Complex selection into simple selection operations."""

    # valExpreBinary_list_ra will contains all the valExpreBinaryOp object with the right order
    valExpreBinary_list_ra = [ra.cond.inputs[1]]
    inputs_0 = ra.cond.inputs[0]
    prev_inputs_0 = None
    while (type(inputs_0.inputs[0]) == radb.ast.ValExprBinaryOp):
        valExpreBinary_list_ra.append(inputs_0.inputs[1])
        prev_inputs_0 = inputs_0
        inputs_0 = inputs_0.inputs[0]
    if type(inputs_0.inputs[0]) != radb.ast.ValExprBinaryOp and prev_inputs_0 == None:
        valExpreBinary_list_ra.append(inputs_0)
    elif prev_inputs_0 != None:
        valExpreBinary_list_ra.append(prev_inputs_0.inputs[0])
    # now
    select_index_number = len(valExpreBinary_list_ra)  # in orde to not include the last valExprBinaryOp
    res = radb.ast.Select(cond=valExpreBinary_list_ra[0], input=ra.inputs[0])
    # it was for i in range(1, select_index_number - 1):
    for i in range(1, select_index_number):
        res = (radb.ast.Select(cond=valExpreBinary_list_ra[i], input=res))
    return res
    # return radb.ast.Select(cond=valExpreBinary_list_ra[-1], input=res)


def rule_break_up_selections(ra):
    if isinstance(ra, radb.ast.Select):
        return break_select(ra)
    elif isinstance(ra, radb.ast.Project):
        return radb.ast.Project(attrs=ra.attrs, input=break_select(ra.inputs[0]))
    elif isinstance(ra, radb.ast.Cross):
        if isinstance(ra.inputs[0], radb.ast.Select):
            return radb.ast.Cross(break_select(ra.inputs[0]), ra.inputs[1])
        elif isinstance(ra.inputs[1], radb.ast.Select):
            return radb.ast.Cross(ra.inputs[0],break_select(ra.inputs[1]))


# L = rule_break_up_selections(ra)
# print(L)
# print('yup2')

# def rule_push_down_selections(ra, dd):
#     pass
#
#
# def rule_merge_selections(ra):
#     pass
#
#
# def rule_introduce_joins(ra):
#     pass
