"""FairFold AI layer.

First source file in the repository. Kept dependency-free on purpose: the
deterministic bias pass is pure text matching, so it must be runnable and
testable without Django, a database, or a configured settings module. Anything
that needs Django belongs behind an import inside the function that needs it,
not at module scope.
"""