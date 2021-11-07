"""
Scipy sparse linear solver with SuperLU backend.
"""

import numpy as np

from scipy.sparse import csc_matrix
from scipy.sparse.linalg import spsolve


class SciPySolver:
    """
    Base class for scipy family solvers.
    """

    def __init__(self):
        pass

    def to_csc(self, A):
        """
        Convert A to scipy.sparse.csc_matrix.

        Parameters
        ----------
        A : kvxopt.spmatrix
            Sparse N-by-N matrix

        Returns
        -------
        scipy.sparse.csc_matrix
            Converted csc_matrix

        """
        ccs = A.CCS
        size = A.size
        data = np.array(ccs[2]).ravel()
        indices = np.array(ccs[1]).ravel()
        indptr = np.array(ccs[0]).ravel()
        return csc_matrix((data, indices, indptr), shape=size)

    def solve(self, A, b):
        """
        Solve linear systems.

        Parameters
        ----------
        A : scipy.csc_matrix
            Sparse N-by-N matrix
        b : numpy.ndarray
            Dense 1-dimensional array of size N

        Returns
        -------
        np.ndarray
            Solution x to `Ax = b`

        """
        raise NotImplementedError

    def linsolve(self, A, b):
        """
        Exactly same functionality as `solve`.
        """
        return self.solve(A, b)

    def clear(self):
        pass


class SpSolve(SciPySolver):
    """
    scipy.sparse.linalg.spsolve Solver.
    """

    def solve(self, A, b):
        A_csc = self.to_csc(A)
        x = spsolve(A_csc, b)
        return np.ravel(x)