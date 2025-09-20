from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, Mapping

ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow)
ALLOWED_CMPOPS = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)
ALLOWED_BOOLOPS = (ast.And, ast.Or)
ALLOWED_UNARYOPS = (ast.USub, ast.UAdd, ast.Not)


class UnsafeExpression(Exception):
    pass


def _eval_node(node: ast.AST, vars: Mapping[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, vars)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, bool)):
            return node.value
        raise UnsafeExpression("Only numeric and boolean constants allowed")
    if isinstance(node, ast.Name):
        if node.id in vars:
            val = vars[node.id]
            if isinstance(val, (int, float, bool)):
                return val
            raise UnsafeExpression("Variable values must be numeric or boolean")
        raise UnsafeExpression(f"Unknown variable: {node.id}")
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ALLOWED_UNARYOPS):
        operand = _eval_node(node.operand, vars)
        if isinstance(node.op, ast.Not):
            return not bool(operand)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand
    if isinstance(node, ast.BinOp) and isinstance(node.op, ALLOWED_BINOPS):
        left = _eval_node(node.left, vars)
        right = _eval_node(node.right, vars)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            return left**right
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ALLOWED_BOOLOPS):
        values = [_eval_node(v, vars) for v in node.values]
        if isinstance(node.op, ast.And):
            result = True
            for v in values:
                result = result and bool(v)
            return result
        if isinstance(node.op, ast.Or):
            result = False
            for v in values:
                result = result or bool(v)
            return result
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, vars)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, vars)
            ok = None
            if isinstance(op, ast.Eq):
                ok = left == right
            elif isinstance(op, ast.NotEq):
                ok = left != right
            elif isinstance(op, ast.Lt):
                ok = left < right
            elif isinstance(op, ast.LtE):
                ok = left <= right
            elif isinstance(op, ast.Gt):
                ok = left > right
            elif isinstance(op, ast.GtE):
                ok = left >= right
            else:
                raise UnsafeExpression("Comparison operator not allowed")
            if not ok:
                return False
            left = right
        return True
    raise UnsafeExpression(
        f"Disallowed expression: {ast.dump(node, include_attributes=False)}"
    )


def evaluate_condition(expr: str, variables: Mapping[str, Any]) -> bool:
    tree = ast.parse(expr, mode="eval")
    # Ensure no dangerous nodes present
    for n in ast.walk(tree):
        if isinstance(
            n,
            (
                ast.Call,
                ast.Attribute,
                ast.Subscript,
                ast.Dict,
                ast.List,
                ast.Tuple,
                ast.Lambda,
                ast.ListComp,
                ast.SetComp,
                ast.DictComp,
                ast.GeneratorExp,
                ast.Import,
                ast.ImportFrom,
                ast.Assign,
                ast.AugAssign,
                ast.While,
                ast.For,
                ast.With,
                ast.If,
                ast.FunctionDef,
                ast.ClassDef,
                ast.Delete,
                ast.Yield,
                ast.YieldFrom,
                ast.Global,
                ast.Nonlocal,
                ast.Raise,
                ast.Try,
                ast.Assert,
            ),
        ):
            raise UnsafeExpression("Disallowed syntax in expression")
    result = _eval_node(tree, variables)
    if not isinstance(result, (bool, int, float)):
        raise UnsafeExpression("Expression must evaluate to a boolean or number")
    return bool(result)


@dataclass
class RuleResult:
    id: str
    passed: bool
    severity: str
    remediation: str | None
    details: dict


def evaluate_rule(rule: dict, inputs: Mapping[str, Any]) -> RuleResult:
    """
    rule structure:
    {"id": "button_min_size", "name": "Min button size",
     "citation": "EN 301 549...",
     "variables": ["button_width_mm", "button_height_mm"],
     "thresholds": {"min_mm": 9.0},
     "condition": "button_width_mm >= min_mm and button_height_mm >= min_mm",
     "severity": "medium", "remediation": "Increase control size"}
    """
    variables = dict(inputs)
    variables.update(rule.get("thresholds") or {})
    cond = rule.get("condition") or ""
    passed = evaluate_condition(cond, variables)
    return RuleResult(
        id=str(rule.get("id")),
        passed=bool(passed),
        severity=str(rule.get("severity", "info")),
        remediation=rule.get("remediation"),
        details={"variables": variables},
    )
