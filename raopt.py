import radb
import radb.ast
import radb.parse

dd = {"Person": {"name": "string", "age": "integer", "gender": "string"}, "Eats": {"name": "string", "pizza": "string"}}

stmt = "\project_{Person.name, Eats.pizza}\select_{Person.name = Eats.name}(Person \cross Eats);"
ra = radb.parse.one_statement_from_string(stmt)
print('yup')






















def rule_break_up_selections(ra):
    pass


def rule_push_down_selections(ra, dd):
    pass


def rule_merge_selections(ra):
    pass


def rule_introduce_joins(ra):
    pass
