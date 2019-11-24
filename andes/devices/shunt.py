import logging
from andes.core.model import Model, ModelData  # NOQA
from andes.core.param import IdxParam, NumParam  # NOQA
from andes.core.var import Algeb, State, ExtAlgeb  # NOQA
logger = logging.getLogger(__name__)


class ShuntData(ModelData):

    def __init__(self, system=None, name=None):
        super().__init__(system, name)

        self.bus = IdxParam(model='Bus', info="idx of connected bus")

        self.Sn = NumParam(default=100.0, info="Power rating", non_zero=True, tex_name=r'S_n')
        self.Vn = NumParam(default=110.0, info="AC voltage rating", non_zero=True, tex_name=r'V_n')
        self.g = NumParam(default=0, info="shunt conductance (real part)", y=True, tex_name=r'g')
        self.b = NumParam(default=0, info="shunt susceptance (positive as capatance)", y=True, tex_name=r'b')
        self.fn = NumParam(default=60.0, info="rated frequency", tex_name=r'f')


class Shunt(ShuntData, Model):
    def __init__(self, system=None, config=None):
        ShuntData.__init__(self)
        Model.__init__(self, system, config)
        self.group = 'StaticShunt'
        self.flags['pflow'] = True

        self.a = ExtAlgeb(model='Bus', src='a', indexer=self.bus, tex_name=r'\theta')
        self.v = ExtAlgeb(model='Bus', src='v', indexer=self.bus, tex_name=r'V')

        self.a.e_str = 'v**2 * g'
        self.v.e_str = '-v**2 * b'