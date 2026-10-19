# Toy problem (planted answer)

Not a real problem. It exists so the tests can prove the whole pipeline works:
the searcher finds a planted "counterexample", the runner saves it, the
independent verifier accepts it, and an alert is raised. A "lying" mode makes
the searcher report a wrong answer, which the verifier must reject, and the
runner must then pause the problem as a suspected bug.
