from pprint import pprint

import radb
import radb.ast
import radb.parse

dd = {"Person": {"name": "string", "age": "integer", "gender": "string"}, "Eats": {"name": "string", "pizza": "string"}}
stmt = "\select_{Person.gender = 'f' and Person.age = 16 and Person.name = 'Amy' and c = d} Person;"
stmt_result = "\select_{Person.gender = 'f'} \select_{Person.age = 16} \select_{Person.name = 'Amy'} \select_{c = d} Person;"
ra = radb.parse.one_statement_from_string(stmt)
ra_result = radb.parse.one_statement_from_string(stmt_result)

valExpreBinary_list_ra = ra.cond.inputs
inputs_ra = ra.inputs[0]
print(ra_result)


def rule_break_up_selections(ra):
    valExpreBinary_list_ra = [ra.cond.inputs[1]]
    inputs_0 = ra.cond.inputs[0]
    prev_inputs_0 = None
    while (type(inputs_0.inputs[0]) == radb.ast.ValExprBinaryOp):
        valExpreBinary_list_ra.append(inputs_0.inputs[1])
        prev_inputs_0 = inputs_0
        inputs_0 = inputs_0.inputs[0]
    if prev_inputs_0 != None:
        valExpreBinary_list_ra.append(prev_inputs_0.inputs[0])

    select_index_number = len(valExpreBinary_list_ra)  # in orde to not include the last valExprBinaryOp
    res = radb.ast.Select(cond=valExpreBinary_list_ra[0], input=ra.inputs[0])
    for i in range(1, select_index_number - 1):
        res = (radb.ast.Select(cond=valExpreBinary_list_ra[i], input=res))

    return radb.ast.Select(cond=valExpreBinary_list_ra[-1], input=res)


r = rule_break_up_selections(ra)
print(r)

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
