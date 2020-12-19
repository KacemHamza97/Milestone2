import re
import radb
import radb.ast
import radb.parse

dd = {}
dd["Person"] = {"name": "string", "age": "integer", "gender": "string"}
dd["Eats"] = {"name": "string", "pizza": "string"}
dd["Serves"] = {"pizzeria": "string", "pizza": "string", "price": "integer"}

stmt = "\select_{Person.name = Eats.name and Person.name = Eats.pizza and Eats.name = 'Amy'} (Person \cross Eats);"
stmt_result = "Person \join_{Person.name = Eats.name and Person.name = Eats.pizza} \select_{Eats.name = 'Amy'} Eats;"
ra = radb.parse.one_statement_from_string(stmt)
ra_result = radb.parse.one_statement_from_string(stmt_result)
print(ra)
print(ra_result)
print('=' * 100)
print(' ')
print(' ')


def input_one_table(ra):
    return str(ra).count('\\cross') == 0


def select_number(ra):
    return str(ra).count('\\select')


def cross_number(ra):
    return str(ra).count('\\cross')


def joint_number(ra):
    return str(ra).count('\\join')


def tris(x, cross_list):
    cross_list_name = [x.rel if isinstance(x, radb.ast.RelRef) else x.relname for x in cross_list]
    x1 = cross_list_name.index(x.inputs[0].rel)
    x2 = cross_list_name.index(x.inputs[1].rel)
    return x1 + x2


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
    cross_object_list.extend(test_cross.inputs[::-1])
    return cross_object_list


def extract_cross_select(ra):
    cross_select_list = [ra.inputs[1]]
    test_cross = ra.inputs[0]

    while (isinstance(test_cross, radb.ast.Cross)):
        cross_select_list.append(test_cross.inputs[1])
        test_cross = test_cross.inputs[0]
    cross_select_list.append(test_cross)

    return cross_select_list


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


def is_cross_select(s):
    return isinstance(s.inputs[0], radb.ast.AttrRef) and isinstance(s.inputs[1], radb.ast.AttrRef) and s.inputs[
        0].name == s.inputs[1].name


def remaining_select(select_list):
    return [s for s in select_list if not is_cross_select(s)]


def is_neither(s):
    return isinstance(s.inputs[0], radb.ast.AttrRef) and isinstance(s.inputs[1], radb.ast.AttrRef)


def replace(table, remaining_list, dd):
    L = []
    for cond in remaining_list:
        if isinstance(table, radb.ast.Rename):
            if table.relname is None:
                a = dd[table.inputs[0].rel].get(cond.inputs[0].name, False)
                if a:
                    L.append(cond)
            else:
                if table.relname == cond.inputs[0].rel:
                    a = dd[table.inputs[0].rel].get(cond.inputs[0].name, False)
                    if a:
                        L.append(cond)
        else:
            if cond.inputs[0].rel == None:
                a = dd[table.rel].get(cond.inputs[0].name, False)
                if a:
                    L.append(cond)
            elif table.rel == cond.inputs[0].rel:
                a = dd[table.rel].get(cond.inputs[0].name, False)
                if a:
                    L.append(cond)

    n = len(L)
    if n == 0:
        return table
    if n == 1:
        return radb.ast.Select(L[0], table)
    elif n > 1:
        res = radb.ast.Select(L[0], table)
        for i in range(1, n):
            res = radb.ast.Select(L[i], res)

        return res

def swap(s):
    if isinstance(s,radb.ast.Select):
        if isinstance(s.inputs[0], radb.ast.Select):
            return radb.ast.Select(s.inputs[0].cond,radb.ast.Select(s.cond,s.inputs[0].inputs[0]))


def select_rest(rest_list, input):
    res = rest_list[0]
    if len(rest_list) == 1:
        return radb.ast.Select(res, input)
    elif len(rest_list) > 1:
        res = radb.ast.Select(res, input)
        for i in range(1, len(rest_list)):
            res = radb.ast.Select(res, rest_list[i])


def push_step1(s_cond_list, cross_list):
    if len(s_cond_list) == 0:
        return cross_list[0]
    return radb.ast.Select(s_cond_list[0], radb.ast.Cross(push_step1(s_cond_list[1:], cross_list[1:]), cross_list[0]))


def push_step2(remaining_list, cross_list, dd):
    if len(cross_list) == 1:
        return replace(cross_list[0], remaining_list, dd)
    return radb.ast.Cross(push_step2(remaining_list, cross_list[1:], dd), replace(
        cross_list[0], remaining_list, dd))


def push_step3(s_cond_list, remaining_list, cross_list, dd):
    if len(cross_list) == 1:
        return replace(cross_list[0], remaining_list, dd)
    return radb.ast.Select(s_cond_list[0],
                           radb.ast.Cross(push_step3(s_cond_list[1:], remaining_list, cross_list[1:], dd), replace(
                               cross_list[0], remaining_list, dd)))


def push_down_rule_selection(ra, dd):
    s_cond_list, cross_list = split_selection_cross(ra)
    remaining_s_list = remaining_select(s_cond_list)[::-1]
    s_cond_list = [e for e in s_cond_list if e not in remaining_s_list]
    s_cond_list.sort(key=lambda x: tris(x, cross_list))
    rest = [e for e in remaining_s_list if is_neither(e)]
    remaining_s_list = [e for e in remaining_s_list if e not in rest]

    if len(remaining_s_list) == 0 and len(rest) == 0:
        return push_step1(s_cond_list, cross_list)
    elif len(remaining_s_list) == 0 and len(rest) != 0:
        return swap(select_rest(rest, push_step1(s_cond_list, cross_list)))
    elif len(remaining_s_list) != 0 and len(s_cond_list) == 0 and len(rest) == 0:
        return push_step2(remaining_s_list, cross_list, dd)
    elif len(remaining_s_list) != 0 and len(s_cond_list) == 0 and len(rest) != 0:
        return select_rest(rest, push_step2(remaining_s_list, cross_list, dd))
    elif len(remaining_s_list) != 0 and len(s_cond_list) != 0 and len(rest) == 0:
        return push_step3(s_cond_list, remaining_s_list, cross_list, dd)
    elif len(remaining_s_list) != 0 and len(s_cond_list) != 0 and len(rest) != 0:
        return swap(select_rest(rest,push_step3(s_cond_list, remaining_s_list, cross_list, dd)))


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


def joint_r(object):
    if isinstance(object, radb.ast.RelRef):
        return object
    if isinstance(object.inputs[0], radb.ast.Rename):
        return object

    if isinstance(object.inputs[0], radb.ast.RelRef):
        return object
    else:
        if isinstance(object.inputs[0], radb.ast.Cross):
            return radb.ast.Join(joint_r(object.inputs[0].inputs[0]), object.cond, object.inputs[0].inputs[1])
        if isinstance(object.inputs[1], radb.ast.RelRef):
            return radb.ast.Join(joint_r(object.inputs[0]), object.cond, object.inputs[1])


def rule_merge_selections_cross(ra):
    L = extract_cross_select(ra)
    selections = [merge_select(s) if isinstance(s, radb.ast.Select) else s for s in L]
    n = len(selections)
    res = selections[-1]
    for i in range(n - 2, -1, -1):
        res = radb.ast.Cross(res, selections[i])
    return res


def rule_break_up_selections(ra):
    if isinstance(ra, radb.ast.RelRef):
        return ra
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
    if isinstance(ra, radb.ast.RelRef):
        return ra
    if input_one_table(ra):
        return ra
    elif isinstance(ra, radb.ast.Project):
        return radb.ast.Project(ra.attrs, push_down_rule_selection(ra.inputs[0], dd))
    elif isinstance(ra, radb.ast.Select):
        return push_down_rule_selection(ra, dd)
    else:
        return ra


def rule_merge_selections(ra):
    if isinstance(ra, radb.ast.RelRef):
        return ra
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
    if isinstance(ra, radb.ast.RelRef):
        return ra
    if input_one_table(ra):
        return ra
    if select_number(ra) == 0:
        return ra
    if isinstance(ra, radb.ast.Cross):
        return ra
    if isinstance(ra, radb.ast.Project):
        return radb.ast.Project(attrs=ra.attrs, input=joint_r(ra.inputs[0]))
    else:
        return joint_r(ra)


print('-' * 100)
b = rule_break_up_selections(ra)
print(b)
print('-' * 100)
p = rule_push_down_selections(b, dd)
print(p)
print('-' * 100)
m = rule_merge_selections(p)
print(m)
print('-' * 100)
L = rule_introduce_joins(m)
print(L)
