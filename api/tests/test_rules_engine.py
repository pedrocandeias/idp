import pytest
from app.rules import UnsafeExpression, evaluate_condition, evaluate_rule


def test_evaluator_basic_arithmetic_and_logic():
    assert evaluate_condition("1 + 2 * 3 == 7", {}) is True
    assert evaluate_condition("not (1 > 2)", {}) is True
    assert (
        evaluate_condition(
            "(a + b) >= min_v and flag", {"a": 5, "b": 3, "min_v": 8, "flag": True}
        )
        is True
    )


def test_evaluator_blocks_unsafe():
    with pytest.raises(UnsafeExpression):
        evaluate_condition("__import__('os').system('echo hi') == 0", {})
    with pytest.raises(UnsafeExpression):
        evaluate_condition("[].__class__", {})


def test_rule_min_button_size_pass_fail():
    rule = {
        "id": "button_min_size",
        "variables": ["button_width_mm", "button_height_mm"],
        "thresholds": {"min_mm": 9.0},
        "condition": "button_width_mm >= min_mm and button_height_mm >= min_mm",
        "severity": "medium",
        "remediation": "Increase control size",
    }

    res = evaluate_rule(rule, {"button_width_mm": 10, "button_height_mm": 9})
    assert res.passed is True

    res = evaluate_rule(rule, {"button_width_mm": 8.9, "button_height_mm": 9})
    assert res.passed is False


def test_rule_contrast_ratio():
    rule = {
        "id": "contrast",
        "variables": ["contrast_ratio"],
        "thresholds": {"min_ratio": 4.5},
        "condition": "contrast_ratio >= min_ratio",
        "severity": "high",
        "remediation": "Increase contrast",
    }
    assert evaluate_rule(rule, {"contrast_ratio": 7.0}).passed is True
    assert evaluate_rule(rule, {"contrast_ratio": 3.0}).passed is False


def test_rule_torque_limit_with_threshold_input():
    # Assume torque_Nm computed externally as force * radius
    rule = {
        "id": "knob_torque_max",
        "variables": ["torque_Nm", "max_torque_Nm"],
        "thresholds": {},
        "condition": "torque_Nm <= max_torque_Nm",
        "severity": "medium",
        "remediation": "Reduce torque or increase diameter.",
    }
    assert evaluate_rule(rule, {"torque_Nm": 0.2, "max_torque_Nm": 0.25}).passed is True
    assert (
        evaluate_rule(rule, {"torque_Nm": 0.3, "max_torque_Nm": 0.25}).passed is False
    )
