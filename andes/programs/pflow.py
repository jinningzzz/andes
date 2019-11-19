import numpy as np
from collections import OrderedDict
from andes.programs.base import ProgramBase
from cvxopt import matrix, sparse
from scipy.optimize import newton_krylov

import logging
logger = logging.getLogger(__name__)


class PFlow(ProgramBase):

    def __init__(self, system=None, config=None):
        super().__init__(system, config)
        self.config.add(OrderedDict((('tol', 1e-6),
                                     ('max_iter', 20))))
        self.models = system.get_models_with_flag('pflow')

        self.converged = False
        self.inc = None
        self.A = None
        self.niter = None
        self.mis = []

    def _initialize(self):
        self.converged = False
        self.inc = None
        self.A = None
        self.niter = None
        self.mis = []
        return self.system.initialize(self.models)

    def nr_step(self):
        """
        Single stepping for Newton Raphson method
        Returns
        -------

        """
        system = self.system
        # evaluate limiters, differential, algebraic, and jacobians
        system.e_clear()
        system.l_update()
        system.f_update()
        system.g_update()
        system.j_update()

        # prepare and solve linear equations
        self.inc = -matrix([matrix(system.dae.f),
                            matrix(system.dae.g)])

        self.A = sparse([[system.dae.fx, system.dae.gx],
                         [system.dae.fy, system.dae.gy]])

        self.inc = self.solver.solve(self.A, self.inc)

        system.dae.x += np.ravel(np.array(self.inc[:system.dae.n]))
        system.dae.y += np.ravel(np.array(self.inc[system.dae.n:]))

        mis = max(abs(matrix([matrix(system.dae.f), matrix(system.dae.g)])))
        self.mis.append(mis)

        system.vars_to_models()

        return mis

    def nr(self):
        """
        Full Newton-Raphson method

        Returns
        -------

        """
        system = self.system
        self._initialize()
        self.niter = 0
        while True:
            mis = self.nr_step()
            logger.info(f'{self.niter}: |F(x)| = {mis:<10g}')

            if mis < self.config.tol:
                self.converged = True
                break
            elif self.niter > self.config.max_iter:
                break
            elif mis > 1e4 * self.mis[0]:
                logger.error('Mismatch increased too fast. Convergence not likely.')
                break
            self.niter += 1

        if not self.converged:
            if abs(self.mis[-1] - self.mis[-2]) < self.config.tol:
                max_idx = np.argmax(np.abs(system.dae.xy))
                name = system.dae.xy_name[max_idx]
                logger.error('Mismatch is not correctable possibly due to large load-generation imbalance.')
                logger.info(f'Largest mismatch on equation associated with <{name}>')

        return self.converged

    def _g_wrapper(self, y):
        """
        Wrapper for algebraic equations to be used with Newton-Krylov general solver

        Parameters
        ----------
        y

        Returns
        -------

        """
        system = self.system
        system.dae.y = y
        system.vars_to_models()
        system.e_clear()

        system.l_update()
        system.f_update()
        g = system.g_update()

        return g

    def newton_krylov(self, verbose=False):
        """
        Full Newton-Krylov method

        Warnings
        --------
        The result might be wrong if limiters are in use!

        Parameters
        ----------
        verbose

        Returns
        -------

        """
        system = self.system
        system.initialize()
        v0 = system.dae.y
        try:
            ret = newton_krylov(self._g_wrapper, v0, verbose=verbose)
        except ValueError as e:
            logger.error('Mismatch is not correctable. Equations may be intrinsically unsolvable.')
            raise e

        return ret
