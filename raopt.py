import re

import radb
import radb.ast
import radb.parse

dd = {}
dd["Person"] = {"name": "string", "age": "integer", "gender": "string"}
dd["Eats"] = {"name": "string", "pizza": "string"}
dd["Serves"] = {"pizzeria": "string", "pizza": "string", "price": "integer"}

stmt = """\project_{Person.name} \select_{Eats.pizza = Serves.pizza and Person.name = Eats.name}
                       ((Person \cross Eats) \cross Serves);"""
stmt_result = """\project_{Person.name} ((Person \join_{Person.name = Eats.name} Eats)
                       \join_{Eats.pizza = Serves.pizza} Serves);"""
ra = radb.parse.one_statement_from_string(stmt)
ra_result = radb.parse.one_statement_from_string(stmt_result)

# print(ra)
# print('-' * 100)
# print(ra_result)
# print('-' * 100)
# print(' ')
# print(' ')


def input_one_table(ra):
    return str(ra).count('\\cross') == 0


def select_number(ra):
    return str(ra).count('\\select')

def cross_number(ra):
    return str(ra).count('\\cross')


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

def cross_restraint_pushdown(ra):
    s,c = split_selection_cross(ra)
    n = len(s)
    res = radb.ast.Cross(c[-2],c[-1])
    res1 = None
    for i in range(n-1,0,-1):
        res0 = radb.ast.Select(cond=s[i],input=res)
        res1 = radb.ast.Cross(res0,c[0])

    return radb.ast.Select(s[0],res1)



def push_down_selections(ra, dd):
    if select_number(ra) == cross_number(ra) >= 2:
        return cross_restraint_pushdown(ra)
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
                    break
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


def merge_select(select_object):
    if isinstance(select_object, radb.ast.RelRef):  # it is a simple select or just a table
        return select_object

    valEcprBinaryOp_list = [select_object.cond]
    test_select = select_object.inputs[0]
    if isinstance(test_select, radb.ast.RelRef):  # it is a simple select or just a table
        return select_object

    if not isinstance(test_select, radb.ast.Cross):

        while (isinstance(test_select.inputs[0], radb.ast.Select)):
                valEcprBinaryOp_list.append(test_select.cond)
                test_select = test_select.inputs[0]

        valEcprBinaryOp_list.append(test_select.cond)
        n = len(valEcprBinaryOp_list)
        res = valEcprBinaryOp_list[0]
        for i in range(1, n):
            res = radb.ast.ValExprBinaryOp(res, radb.ast.sym.AND, valEcprBinaryOp_list[i])

        return radb.ast.Select(cond=res, input=test_select.inputs[0])
    else:
        return radb.ast.Select(cond=valEcprBinaryOp_list[0], input=test_select)

def extract_cross_select(ra):
    cross_select_list = [ra.inputs[1]]
    test_cross = ra.inputs[0]

    while (isinstance(test_cross, radb.ast.Cross)):
        cross_select_list.append(test_cross.inputs[1])
        test_cross = test_cross.inputs[0]
    cross_select_list.append(test_cross)

    return cross_select_list


def joint_r(object):
    if isinstance(object, radb.ast.RelRef):
        return object

    if isinstance(object.inputs[0], radb.ast.RelRef):
        return object
    else:
        if isinstance(object.inputs[0], radb.ast.Cross):
            return radb.ast.Join(joint_r(object.inputs[0].inputs[0]), object.cond, object.inputs[0].inputs[1])
        if isinstance(object.inputs[1], radb.ast.RelRef):
            return radb.ast.Join(joint_r(object.inputs[0]), object.cond, object.inputs[1])


def rule_break_up_selections(ra):
    if str(ra).count('and') == 0:
        return ra
    if isinstance(ra, radb.ast.Select):
        return break_select(ra)
    elif isinstance(ra, radb.ast.Project):
        return radb.ast.Project(attrs=ra.attrs, input=break_select(ra.inputs[0]))
    elif isinstance(ra, radb.ast.Cross):
        if isinstance(ra.inputs[0], radb.ast.Select):
            return radb.ast.Cross(break_select(ra.inputs[0]), ra.inputs[1])
        elif isinstance(ra.inputs[1], radb.ast.Select):
            return radb.ast.Cross(ra.inputs[0], break_select(ra.inputs[1]))


def rule_push_down_selections(ra, dd):
    dd["Frequents"] = {}
    if input_one_table(ra):
        return ra
    elif isinstance(ra, radb.ast.Project):
        return radb.ast.Project(ra.attrs, push_down_selections(ra.inputs[0], dd))
    else:
        return push_down_selections(ra, dd)


def rule_merge_selections_cross(ra):
    L = extract_cross_select(ra)
    selections = [merge_select(s) if isinstance(s, radb.ast.Select) else s for s in L]
    n = len(selections)
    res = selections[-1]
    for i in range(n - 2, -1, -1):
        res = radb.ast.Cross(res, selections[i])
    return res


def rule_merge_selections(ra):
    if select_number(ra) == 1:
        return ra
    if isinstance(ra, radb.ast.Select):
        return merge_select(ra)
    if isinstance(ra, radb.ast.Cross):
        return rule_merge_selections_cross(ra)
    if isinstance(ra, radb.ast.Project):
        if isinstance(ra.inputs[0], radb.ast.Select):
            return radb.ast.Project(attrs=ra.attrs, input=merge_select(ra.inputs[0]))
        elif isinstance(ra.inputs[0], radb.ast.Cross):
            return radb.ast.Project(attrs=ra.attrs, input=rule_merge_selections_cross(ra.inputs[0]))


def rule_introduce_joins(ra):
    if input_one_table(ra):
        return ra
    if isinstance(ra, radb.ast.Project):
        return radb.ast.Project(attrs=ra.attrs, input=joint_r(ra.inputs[0]))
    else:
        return joint_r(ra)




# b = rule_break_up_selections(ra)
# print(b)
# print('-' * 100)
# s = rule_push_down_selections(b, dd)
# print(s)
# print('-' * 100)
# m = rule_merge_selections(s)
# print(m)
# print('-' * 100)
# L = rule_introduce_joins(m)
# print(L)
