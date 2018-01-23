import cmath
def isclose(x, y, rel_tol=1e-9, abs_tol=0.0):
    try:
        return cmath.isclose(x, y, rel_to, abs_tol)
    except AttributeError:
        return abs(x-y) <= max(rel_tol * max(abs(x), abs(y)), abs_tol)

