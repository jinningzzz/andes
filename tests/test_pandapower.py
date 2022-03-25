"""
Test ANDES-pandapower interface.
"""

import unittest
import numpy as np
from andes.interop.pandapower import to_pandapower, make_link_table
from math import pi
import andes


try:
    import pandapower as pp
    HAVE_PANDAPOWER = True
except ImportError:
    HAVE_PANDAPOWER = False


@unittest.skipUnless(HAVE_PANDAPOWER, "pandapower not available")
class TestPandapower(unittest.TestCase):
    """
    Tests for the ANDES-pandapower interface.
    """

    def setUp(self) -> None:
        """
        Test setup. This is executed before each test case.
        """

        ssa = andes.load(andes.get_case('ieee14/ieee14_ieeet1.xlsx'),
                         setup=True,
                         no_output=True,
                         default_config=True)
        ssp = to_pandapower(ssa)

        ssa.PFlow.run()
        pp.runpp(ssp)

        self.v_andes = ssa.Bus.v.v
        self.a_andes = ssa.Bus.a.v * 180 / pi

        self.v_pp = ssp.res_bus['vm_pu']
        self.a_pp = ssp.res_bus['va_degree']

        self.link_table = make_link_table(ssa)

    def test_to_pandapower(self):

        np.testing.assert_almost_equal(self.v_andes, self.v_pp, decimal=6)
        np.testing.assert_almost_equal(self.a_andes, self.a_pp, decimal=6)

    def test_make_link_table(self):
        ridx = self.link_table[self.link_table['syn_idx'] == 'GENROU_1'].index
        c_bus = self.link_table['bus_name'].iloc[ridx].astype(str) == 'BUS1'
        c_exc = self.link_table['exc_idx'].iloc[ridx].astype(str) == 'ESST3A_2'
        c_stg = self.link_table['stg_idx'].iloc[ridx].astype(str) == '1'
        c_gov = self.link_table['gov_idx'].iloc[ridx].astype(str) == 'TGOV1_1'
        return c_bus[0] and c_exc[0] and c_stg[0] and c_gov[0]
        # make_link_table
