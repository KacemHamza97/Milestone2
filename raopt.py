from pprint import pprint
import re

import radb
import radb.ast
import radb.parse

dd = {}
dd["Person"] = {"name": "string", "age": "integer", "gender": "string"}
dd["Eats"] = {"name": "string", "pizza": "string"}
dd["Serves"] = {"pizzeria": "string", "pizza": "string", "price": "integer"}

stmt = "\select_{Person.name = 'Amy'} \select_{gender = 'f'} \select_{age = 16} Person;"
stmt_result = "\select_{Person.name = 'Amy' and gender = 'f' and age = 16} Person;"
ra = radb.parse.one_statement_from_string(stmt)
ra_result = radb.parse.one_statement_from_string(stmt_result)

print('input')
print(ra)
print('expected')
print(ra_result)
print('-' * 10)


def input_one_table(ra):
    return str(ra).count('\\cross') == 0


def select_number(ra):
    return str(ra).count('\\select')


def break_select(ra):
    """ Breaks up Complex selection into simple selection operations."""

    # valExpreBinary_list_ra will contain all the valExprBinaryOp objects in the right order.
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

    # The creation of the desired Selection object.
    select_index_number = len(valExpreBinary_list_ra)
    res = radb.ast.Select(cond=valExpreBinary_list_ra[0], input=ra.inputs[0])
    for i in range(1, select_index_number):
        res = (radb.ast.Select(cond=valExpreBinary_list_ra[i], input=res))
    return res


def rule_break_up_selections(ra):
    if isinstance(ra, radb.ast.Select):
        return break_select(ra)
    elif isinstance(ra, radb.ast.Project):
        return radb.ast.Project(attrs=ra.attrs, input=break_select(ra.inputs[0]))
    elif isinstance(ra, radb.ast.Cross):
        if isinstance(ra.inputs[0], radb.ast.Select):
            return radb.ast.Cross(break_select(ra.inputs[0]), ra.inputs[1])
        elif isinstance(ra.inputs[1], radb.ast.Select):
            return radb.ast.Cross(ra.inputs[0], break_select(ra.inputs[1]))


def clean_query(sql_query):
    """removes all successive whitespaces >2 and replace them with one whitespace.
        also it removes the white spaces at the start and at the end of the sql_query"""
    return re.sub("\s\s+", " ", sql_query).strip()


def cross_tolist(cross_object):
    cross_object_list = [cross_object.inputs[1]]
    test_cross = cross_object.inputs[0]
    if not isinstance(test_cross, radb.ast.Cross):
        cross_object_list.append(test_cross)
        return cross_object_list
    while (isinstance(test_cross.inputs[0], radb.ast.Cross)):
        cross_object_list.append(test_cross.inputs[1])
        test_cross = test_cross.inputs[0]
    cross_object_list.extend(test_cross.inputs)
    return cross_object_list


def split_selection_cross(ra):
    cross_list = []
    list_selection_cond = [ra.cond]
    test_cross = ra.inputs[0]
    while (isinstance(test_cross, radb.ast.Select)):
        list_selection_cond.append(test_cross.cond)
        test_cross = test_cross.inputs[0]

    if isinstance(test_cross, radb.ast.Cross):
        cross_list = cross_tolist(test_cross)

    return list_selection_cond, cross_list


def push_down_selections(ra, dd):
    list_selection_cond, cross_list = split_selection_cross(ra)
    remaining_selection_list = []
    cross_res = cross_list[:]
    for s in list_selection_cond:
        for i, c in enumerate(cross_list):
            if isinstance(s.inputs[0], radb.ast.AttrRef) and isinstance(s.inputs[1], radb.ast.AttrRef):
                remaining_selection_list.append(s)
                break
            else:
                if isinstance(c, radb.ast.Rename):
                    if s.inputs[0].rel == c.relname:
                        a = dd[c.inputs[0].rel].get(s.inputs[0].name, False)
                    else:
                        continue
                else:
                    a = dd[c.rel].get(s.inputs[0].name, False)

                if a:
                    cross_res[i] = radb.ast.Select(cond=s, input=c)
    n = len(cross_res)
    c_res = cross_res[1]
    for c in range(2, n):
        c_res = radb.ast.Cross(c_res, cross_res[c])

    c_res = radb.ast.Cross(c_res, cross_res[0])

    if len(remaining_selection_list) == 0:
        return c_res
    s_res = radb.ast.Select(remaining_selection_list[-1], c_res)
    for s in range(len(remaining_selection_list) - 1):
        s_res = radb.ast.Select(remaining_selection_list[s], s_res)
    return s_res


def rule_push_down_selections(ra, dd):
    dd["Frequents"] = {}
    if input_one_table(ra):
        return ra
    elif isinstance(ra, radb.ast.Project):
        return radb.ast.Project(ra.attrs, push_down_selections(ra.inputs[0], dd))
    else:
        return push_down_selections(ra, dd)


def merge_select(select_object):
    valEcprBinaryOp_list = [select_object.cond]
    test_select = select_object.inputs[0]
    if not isinstance(test_select, radb.ast.Select):  # it is a simple select then
        return select_object

    while (isinstance(test_select.inputs[0], radb.ast.Select)):
        valEcprBinaryOp_list.append(test_select.cond)
        test_select = test_select.inputs[0]

    valEcprBinaryOp_list.append(test_select.cond)
    n = len(valEcprBinaryOp_list)
    res = valEcprBinaryOp_list[0]
    for i in range(1, n):
        res = radb.ast.ValExprBinaryOp(res, radb.ast.sym.AND, valEcprBinaryOp_list[i])

    return radb.ast.Select(cond=res, input=test_select.inputs[0])


def extract_cross_select(ra):
    cross_select_list = [ra.inputs[1]]
    test_cross = ra.inputs[0]
    while (isinstance(test_cross, radb.ast.Cross)):
        cross_select_list.append(test_cross.inputs[1])
        test_cross = test_cross.inputs[0]
    cross_select_list.append(test_cross)

    return cross_select_list


def rule_merge_selections(ra):
    if select_number(ra) == 1:
        return ra
    if isinstance(ra,radb.ast.Select):
        return merge_select(ra)
    if isinstance(ra, radb.ast.Cross):
        L = extract_cross_select(ra)
        selections = [merge_select(s) for s in L]
        n = len(selections)
        res = selections[-1]
        for i in range(n-2,-1,-1):
            res = radb.ast.Cross(res,selections[i])
        return res




print(rule_merge_selections(ra))

# def rule_introduce_joins(ra):
#     pass
#
# print('result')
# merge = rule_merge_selections(ra)
# print(merge)
# res = merge_select(ra)
# print(res)
# cross_object = radb.parse.one_statement_from_string("(((Person \cross Eats) \cross Serves) \cross frequences);")
# L = cross_tolist(cross_object)
# s, c = split_selection_cross(ra)
# print(s)
# print(c)

# s = rule_push_down_selections(ra, dd)
# print(s)
# print(cross)
# print(type(cross))
# print('yup')
