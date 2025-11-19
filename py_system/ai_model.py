"""AI reply helpers for Aizeeno Chat.

This module provides:
- greeting handling
- safe math evaluation (AST-based) including math.* functions
- simple time and small talk responses
- optional Azure OpenAI forwarding if environment variables are set

The math evaluator is implemented to avoid arbitrary code execution.
"""
from datetime import datetime
import ast
import math
import re
from typing import Any, Optional


_ALLOWED_NAMES = {name: getattr(math, name) for name in dir(math) if not name.startswith("_")}
_ALLOWED_NAMES.update({"abs": abs, "round": round, "pow": pow})


def _is_safe_expr(expr: str) -> bool:
    try:
        tree = ast.parse(expr, mode="eval")
    except Exception:
        return False

    for node in ast.walk(tree):
        # allowed node types
        if isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Load, ast.Constant, ast.Name, ast.Tuple)):
            continue
        if isinstance(node, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd, ast.FloorDiv)):
            continue
        return False

    # Ensure names are allowed
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id not in _ALLOWED_NAMES:
                return False

    return True


def safe_eval(expr: str) -> Any:
    expr = expr.strip()
    if not expr:
        raise ValueError("Empty expression")

    expr = expr.replace("^", "**")

    if not _is_safe_expr(expr):
        raise ValueError("Unsafe expression")

    compiled = compile(ast.parse(expr, mode="eval"), "<ast>", "eval")
    return eval(compiled, {"__builtins__": {}}, _ALLOWED_NAMES)


def _extract_math(text: str) -> Optional[str]:
    # find contiguous substrings that look like math expressions (digits, operators, parentheses, decimal point)
    candidates = re.findall(r"[0-9\(\)\+\-\*/\^%\. ,]+", text)
    candidates = [c.strip() for c in candidates if re.search(r"\d", c)]
    if not candidates:
        return None
    # prefer the longest candidate
    return max(candidates, key=len)


# No external API integration: replies are generated locally (greetings, math, time, small talk)


def get_ai_reply(user_input: str) -> str:
    if not user_input:
        return "I didn’t quite catch that. Can you say it again?"

    text = user_input.strip()
    lower = text.lower()

    # exact hi
    if lower == "hi":
        return "hi"

    greetings = ["hi", "hey", "hello", "yo", "sup"]
    if any(re.search(rf"\b{g}\b", lower) for g in greetings):
        return "Hey there 👋! How are you doing today?"

    # Try evaluate as math directly
    try:
        result = safe_eval(text)
        return str(result)
    except Exception:
        pass

    # Try extract math substring
    expr = _extract_math(text)
    if expr:
        try:
            result = safe_eval(expr)
            return str(result)
        except Exception:
            pass

    # Time
    if "time" in lower:
        return f"The current time is {datetime.now().strftime('%I:%M %p')}"

    # local small-talk / fallback only (no external API calls)

    # small talk
    if "how are you" in lower:
        return "I'm doing great! Thanks for asking 😄. How about you?"

    if "your name" in lower or "who are you" in lower:
        return "I’m Aizeeno, your AI assistant 🤖 here to help with anything you need!"

    if "bye" in lower or "goodbye" in lower:
        return "Goodbye! See you later 👋"

    return "I'm not sure I understood that, but I'm learning every day! 😊"
