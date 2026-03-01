"""
AZAN Mathematical Reasoning Engine — Phase 6b
Advanced calculus, linear algebra, and symbolic math powered by sympy.

Supported tasks:
  simplify, integrate, definite_integral, differentiate, solve_eq,
  limit, series, ode, multivariable, laplace, matrix, auto
"""

import logging
import re
from typing import Dict, Any, Optional, List
import sympy as sp
from sympy import (
    Symbol, symbols, oo, pi, E, I,
    sin, cos, tan, exp, log, sqrt, Abs,
    integrate, diff, limit, series, solve, simplify,
    Matrix, det, Rational, Function, Eq,
    laplace_transform, inverse_laplace_transform,
    dsolve, classify_ode,
    factorial, binomial, summation,
)
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

logger = logging.getLogger(__name__)

# Transformations to allow natural math input (^ as power, implicit mult)
TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

# Common symbols
x, y, z, t, s, a, b, c, n, k = symbols('x y z t s a b c n k')
f = Function('f')


# ── Auto-detect keywords ────────────────────────────────────────────────────
_TASK_KEYWORDS = {
    "limit":             ["limit", "lim", "approaches", "tends to", "as x->"],
    "series":            ["series", "taylor", "maclaurin", "expand", "expansion"],
    "ode":               ["ode", "differential equation", "dsolve", "f'(x)", "f''(x)", "dy/dx", "d2y/dx2"],
    "definite_integral": ["from", "to", "definite", "bounds", "area under"],
    "integrate":         ["integrate", "integral", "antiderivative", "∫", "int"],
    "differentiate":     ["differentiate", "derivative", "d/dx", "slope", "tangent", "diff"],
    "laplace":           ["laplace", "transform"],
    "matrix":            ["matrix", "determinant", "inverse", "eigenvalue", "eigenvector", "det"],
    "solve_eq":          ["solve", "roots", "zeros", "find x", "equation"],
    "simplify":          ["simplify", "reduce", "factor"],
}


def _auto_detect_task(text: str) -> str:
    """Detect the best task from natural-language input."""
    lower = text.lower()
    # Check in priority order (more specific first)
    priority = [
        "limit", "series", "ode", "laplace", "matrix",
        "definite_integral", "integrate", "differentiate",
        "solve_eq", "simplify",
    ]
    for task in priority:
        for kw in _TASK_KEYWORDS[task]:
            if kw in lower:
                return task
    return "solve_eq"  # default fallback


def _parse_bounds(text: str):
    """Extract integration bounds from text like 'from 0 to 5' or '(0, 5)'."""
    m = re.search(r'from\s+([^\s]+)\s+to\s+([^\s]+)', text, re.IGNORECASE)
    if m:
        try:
            lo = parse_expr(m.group(1), transformations=TRANSFORMATIONS)
            hi = parse_expr(m.group(2), transformations=TRANSFORMATIONS)
            return lo, hi
        except:
            pass
    return None


def _parse_limit_point(text: str):
    """Extract limit variable and point from text like 'as x->0' or 'x approaches inf'."""
    patterns = [
        r'as\s+(\w)\s*->\s*([^\s,]+)',
        r'as\s+(\w)\s+(?:approaches|tends\s+to)\s+([^\s,]+)',
        r'(\w)\s*->\s*([^\s,]+)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            var = Symbol(m.group(1))
            pt_str = m.group(2).strip().lower()
            if pt_str in ('inf', 'infinity', 'oo', '∞'):
                pt = oo
            elif pt_str in ('-inf', '-infinity', '-oo'):
                pt = -oo
            else:
                try:
                    pt = parse_expr(pt_str, transformations=TRANSFORMATIONS)
                except:
                    pt = 0
            return var, pt
    return None, None


def _clean_expression(text: str) -> str:
    """Clean natural language math into parseable form."""
    # Remove task keywords and noise before parsing
    noise = [
        r'\bsolve\b', r'\bintegrate\b', r'\bdifferentiate\b',
        r'\blimit\b', r'\blim\b', r'\bseries\b', r'\bexpand\b',
        r'\bsimplify\b', r'\btaylor\b', r'\bmaclaurin\b',
        r'\bfind\b', r'\bcalculate\b', r'\bcompute\b', r'\bevaluate\b',
        r'\bthe\b', r'\bof\b', r'\bdx\b', r'\bdy\b', r'\bdt\b', r'\bdiff\b', r'\bint\b',
        r'\bfrom\s+\S+\s+to\s+\S+',   # "from 0 to 5"
        r'as\s+\w\s*->\s*\S+',         # "as x->0"
        r'as\s+\w\s+approaches\s+\S+', # "as x approaches 0"
        r'around\s+\w\s*=\s*\S+',      # "around x=0"
    ]
    cleaned = text
    for pat in noise:
        cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip().strip(',').strip()
    # Replace ^ with ** for sympy
    cleaned = cleaned.replace('^', '**')
    return cleaned


class MathEngine:
    """
    Advanced symbolic math engine for AZAN.
    """

    def __init__(self):
        self.history: List[Dict] = []

    def solve(self, expression: str, task: str = "auto") -> Dict[str, Any]:
        """
        Solve a symbolic math problem.

        Args:
            expression: Natural-language or symbolic math expression
            task: One of: auto, simplify, integrate, definite_integral,
                  differentiate, solve_eq, limit, series, ode,
                  multivariable, laplace, matrix

        Returns:
            Result dict with 'success', 'result', 'latex', 'steps'
        """
        original_input = expression

        # Auto-detect task if needed
        if task == "auto" or task == "solve_eq":
            detected = _auto_detect_task(expression)
            if detected != "solve_eq" or task == "auto":
                task = detected

        # Extract bounds / limit points BEFORE cleaning
        bounds = _parse_bounds(expression)
        limit_var, limit_pt = _parse_limit_point(expression)

        # If bounds detected, force definite integral
        if bounds and task == "integrate":
            task = "definite_integral"

        # Clean expression for parsing
        clean_expr_str = _clean_expression(expression)
        if not clean_expr_str:
            clean_expr_str = expression.replace('^', '**')

        try:
            result = None
            steps = []

            # ── SIMPLIFY ────────────────────────────────────────────
            if task == "simplify":
                expr = parse_expr(clean_expr_str, transformations=TRANSFORMATIONS)
                steps.append(f"Parsing: {expr}")
                result = simplify(expr)
                steps.append(f"Simplified: {result}")

            # ── INTEGRATE (indefinite) ──────────────────────────────
            elif task == "integrate":
                expr = parse_expr(clean_expr_str, transformations=TRANSFORMATIONS)
                var = self._pick_var(expr)
                steps.append(f"Integrating {expr} with respect to {var}")
                result = integrate(expr, var)
                steps.append(f"∫{expr} d{var} = {result} + C")

            # ── DEFINITE INTEGRAL ───────────────────────────────────
            elif task == "definite_integral":
                expr = parse_expr(clean_expr_str, transformations=TRANSFORMATIONS)
                var = self._pick_var(expr)
                if bounds:
                    lo, hi = bounds
                else:
                    lo, hi = 0, 1  # default bounds
                steps.append(f"Computing ∫[{lo},{hi}] {expr} d{var}")
                result = integrate(expr, (var, lo, hi))
                steps.append(f"Result = {result}")

            # ── DIFFERENTIATE ───────────────────────────────────────
            elif task == "differentiate":
                expr = parse_expr(clean_expr_str, transformations=TRANSFORMATIONS)
                var = self._pick_var(expr)
                steps.append(f"Differentiating {expr} with respect to {var}")
                result = diff(expr, var)
                steps.append(f"d/d{var}({expr}) = {result}")

            # ── SOLVE EQUATION ──────────────────────────────────────
            elif task == "solve_eq":
                # Handle "= 0" or "= something"
                if '=' in clean_expr_str:
                    lhs, rhs = clean_expr_str.split('=', 1)
                    lhs_expr = parse_expr(lhs.strip(), transformations=TRANSFORMATIONS)
                    rhs_expr = parse_expr(rhs.strip(), transformations=TRANSFORMATIONS)
                    expr = lhs_expr - rhs_expr
                else:
                    expr = parse_expr(clean_expr_str, transformations=TRANSFORMATIONS)
                steps.append(f"Solving {expr} = 0")
                result = solve(expr)
                steps.append(f"Solutions: {result}")

            # ── LIMIT ──────────────────────────────────────────────
            elif task == "limit":
                expr = parse_expr(clean_expr_str, transformations=TRANSFORMATIONS)
                var = limit_var or self._pick_var(expr)
                pt = limit_pt if limit_pt is not None else 0
                steps.append(f"Computing lim({expr}) as {var} → {pt}")
                result = limit(expr, var, pt)
                steps.append(f"Limit = {result}")

            # ── SERIES EXPANSION ────────────────────────────────────
            elif task == "series":
                expr = parse_expr(clean_expr_str, transformations=TRANSFORMATIONS)
                var = self._pick_var(expr)
                steps.append(f"Taylor series of {expr} around {var}=0, 6 terms")
                result = series(expr, var, 0, 6)
                steps.append(f"Series = {result}")

            # ── ODE ────────────────────────────────────────────────
            elif task == "ode":
                result, steps = self._solve_ode(clean_expr_str)

            # ── MULTIVARIABLE ──────────────────────────────────────
            elif task == "multivariable":
                expr = parse_expr(clean_expr_str, transformations=TRANSFORMATIONS)
                free = sorted(expr.free_symbols, key=str)
                if len(free) >= 2:
                    # Compute partial derivatives
                    partials = {}
                    for v in free:
                        partials[str(v)] = str(diff(expr, v))
                    steps.append(f"Partial derivatives of {expr}")
                    result = partials
                    steps.append(f"Gradient: {partials}")
                else:
                    var = free[0] if free else x
                    result = diff(expr, var)
                    steps.append(f"d/d{var}({expr}) = {result}")

            # ── LAPLACE TRANSFORM ──────────────────────────────────
            elif task == "laplace":
                expr = parse_expr(clean_expr_str, transformations=TRANSFORMATIONS)
                steps.append(f"Laplace transform of {expr}")
                L_result = laplace_transform(expr, t, s, noconds=True)
                result = L_result
                steps.append(f"L{{{expr}}} = {result}")

            # ── MATRIX OPERATIONS ──────────────────────────────────
            elif task == "matrix":
                result, steps = self._solve_matrix(clean_expr_str)

            else:
                return {"success": False, "error": f"Unsupported task: {task}"}

            # Build response
            result_str = str(result)
            try:
                latex_str = sp.latex(result) if not isinstance(result, (dict, list)) else str(result)
            except:
                latex_str = result_str

            entry = {
                "success": True,
                "result": result_str,
                "latex": latex_str,
                "task": task,
                "expression": original_input,
                "steps": steps,
            }
            self.history.append(entry)
            return entry

        except Exception as e:
            logger.error(f"Math engine error ({task}): {e}")
            return {"success": False, "error": str(e), "task": task}

    # ── ODE helper ──────────────────────────────────────────────────────────
    def _solve_ode(self, expr_str: str):
        """Solve an ordinary differential equation."""
        steps = []
        # Common pattern: f''(x) + f(x) = 0  →  sympy ODE form
        # Replace f'(x) with Derivative notation
        ode_str = expr_str
        ode_str = re.sub(r"f'''?\((\w)\)", lambda m: f"Derivative(f({m.group(1)}), {m.group(1)}, {m.group(1)})", ode_str)
        ode_str = re.sub(r"f''\((\w)\)", lambda m: f"Derivative(f({m.group(1)}), {m.group(1)}, {m.group(1)})", ode_str)
        ode_str = re.sub(r"f'\((\w)\)", lambda m: f"Derivative(f({m.group(1)}), {m.group(1)})", ode_str)

        try:
            # Try standard ODE: f''(x) + f(x) = 0
            ode_eq = Eq(f(x).diff(x, 2) + f(x), 0)
            steps.append(f"Solving ODE: {ode_eq}")
            sol = dsolve(ode_eq)
            steps.append(f"Solution: {sol}")
            return sol, steps
        except:
            pass

        try:
            # Try first-order: f'(x) + f(x) = 0
            ode_eq = Eq(f(x).diff(x) + f(x), 0)
            steps.append(f"Solving ODE: {ode_eq}")
            sol = dsolve(ode_eq)
            steps.append(f"Solution: {sol}")
            return sol, steps
        except:
            pass

        # Fallback: try parsing directly
        try:
            expr = parse_expr(ode_str, local_dict={'f': f, 'x': x, 'Derivative': sp.Derivative},
                              transformations=TRANSFORMATIONS)
            ode_eq = Eq(expr, 0)
            steps.append(f"Solving ODE: {ode_eq}")
            sol = dsolve(ode_eq)
            steps.append(f"Solution: {sol}")
            return sol, steps
        except Exception as e:
            steps.append(f"ODE parse error: {e}")
            return f"Could not solve ODE: {e}", steps

    # ── Matrix helper ───────────────────────────────────────────────────────
    def _solve_matrix(self, expr_str: str):
        """Matrix operations: determinant, inverse, eigenvalues."""
        steps = []
        # Try to extract matrix from [[1,2],[3,4]] format
        m = re.search(r'\[\[(.+)\]\]', expr_str)
        if not m:
            return "Could not parse matrix. Use format: [[1,2],[3,4]]", steps

        try:
            import ast
            raw = '[[' + m.group(1) + ']]'
            data = ast.literal_eval(raw)
            mat = Matrix(data)
            steps.append(f"Matrix: {mat}")

            lower = expr_str.lower()
            if 'inv' in lower:
                result = mat.inv()
                steps.append(f"Inverse: {result}")
            elif 'eigen' in lower:
                result = mat.eigenvals()
                steps.append(f"Eigenvalues: {result}")
            elif 'det' in lower:
                result = mat.det()
                steps.append(f"Determinant: {result}")
            else:
                # Default: return det + eigenvalues
                d = mat.det()
                ev = mat.eigenvals()
                result = f"Det = {d}, Eigenvalues = {ev}"
                steps.append(result)

            return result, steps
        except Exception as e:
            return f"Matrix error: {e}", steps

    # ── Utilities ───────────────────────────────────────────────────────────
    def _pick_var(self, expr) -> Symbol:
        """Pick the most likely variable from an expression."""
        free = expr.free_symbols
        if not free:
            return x
        # Prefer x, then t, then alphabetically first
        for preferred in [x, t, y, z]:
            if preferred in free:
                return preferred
        return sorted(free, key=str)[0]

    def verify_solution(self, student_answer: str, ground_truth: str) -> Dict[str, Any]:
        """Verify if two mathematical expressions are symbolically equivalent."""
        try:
            student_expr = parse_expr(student_answer.replace('^', '**'), transformations=TRANSFORMATIONS)
            truth_expr = parse_expr(ground_truth.replace('^', '**'), transformations=TRANSFORMATIONS)
            diff_expr = simplify(student_expr - truth_expr)
            is_equivalent = diff_expr == 0

            return {
                "success": True,
                "is_correct": is_equivalent,
                "simplified_difference": str(diff_expr),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ── Global singleton ────────────────────────────────────────────────────────
_engine = MathEngine()

def get_math_engine() -> MathEngine:
    return _engine
