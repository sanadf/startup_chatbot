"""Light, flexible handling of messages outside investment sourcing.

The chatbot stays focused on sourcing, but a short, honest answer to a casual
question reads far better than a flat refusal, so simple questions get answered
before the conversation is steered back.
"""

import ast
import operator
import re

MAX_EXPONENT = 64
MAX_OPERANDS = 20

_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

PIVOTS = [
    "Now, what I am actually built for: give me an investment thesis — sector, "
    "geography and funding stage — and I will research matching startups.",
    "Back to my job: describe the startups you are looking for, or ask me about "
    "a company from a report.",
]


def _evaluate(node: ast.AST, budget: list[int]) -> float:
    budget[0] -= 1
    if budget[0] < 0:
        raise ValueError("expression too long")

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("unsupported constant")
        return node.value

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_evaluate(node.operand, budget))

    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
        left = _evaluate(node.left, budget)
        right = _evaluate(node.right, budget)
        if isinstance(node.op, ast.Pow) and abs(right) > MAX_EXPONENT:
            raise ValueError("exponent too large")
        return _BINARY_OPS[type(node.op)](left, right)

    raise ValueError("unsupported expression")


def _format(value: float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{round(value, 6):g}"
    return str(value)


def arithmetic_answer(message: str) -> str | None:
    """Evaluate a plain arithmetic question, or return None if it is not one."""
    text = re.sub(r"[\s?=]+$", "", message.strip())
    text = re.sub(
        r"^(what(\s+is|'?s)|calculate|compute|how much is|solve)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = text.replace("x", "*").replace("×", "*").replace("÷", "/").strip()

    if not text or not re.fullmatch(r"[\d\s+\-*/().%^]+", text):
        return None

    if not re.search(r"\d", text) or not re.search(r"[+\-*/%^]", text):
        return None

    try:
        tree = ast.parse(text.replace("^", "**"), mode="eval")
        value = _evaluate(tree.body, [MAX_OPERANDS])
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError):
        return None

    expression = text.replace("**", "^")
    return f"{expression} = {_format(value)}"


def offtopic_reply(message: str) -> str:
    """A brief, friendly answer where possible, then a nudge back on topic."""
    computed = arithmetic_answer(message)

    if computed:
        return f"{computed}.\n\n{PIVOTS[0]}"

    return (
        "That one is outside what I know — I only work with startup, funding and "
        f"company data.\n\n{PIVOTS[1]}"
    )
