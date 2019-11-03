from andes.models.base import Model  # NOQA
from andes.models.base import ModelData  # NOQA
from andes.models.bus import BusNew  # NOQA
from andes.system import SystemNew

import numpy as np  # NOQA
import unittest


class TestSystem(unittest.TestCase):
    def setUp(self) -> None:
        self.ss = SystemNew()
        self.n_bus = 10000
        for i in range(self.n_bus):
            self.ss.add('BusNew', Vn=100, idx=i)
            self.ss.add('PQNew', bus=i, idx=1)

        self.ss.set_address()
        self.ss.finalize_add()
        self.ss.link_external()
        self.ss.PQNew.convert_equations()
        self.ss.PQNew.convert_jacobians()

    def test_names(self):
        self.assertTrue('BusNew' in self.ss.models)
        self.assertTrue('PQNew' in self.ss.models)

    def test_variable_address(self):
        self.assertSequenceEqual(self.ss.BusNew.a.a.tolist(), list(range(self.n_bus)))
        self.assertSequenceEqual(self.ss.BusNew.v.a.tolist(), list(range(self.n_bus, 2 * self.n_bus)))

        self.assertSequenceEqual(self.ss.PQNew.a.a.tolist(), list(range(self.n_bus)))
        self.assertSequenceEqual(self.ss.PQNew.v.a.tolist(), list(range(self.n_bus, 2 * self.n_bus)))
