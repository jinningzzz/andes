"""
Classes for Center of Inertia calculation.
Added VSG into COI calculation.
"""
import numpy as np

from andes.core.param import ExtParam
from andes.core.service import NumRepeat, IdxRepeat, BackRef
from andes.core.service import NumReduce, RefFlatten, ExtService, ConstService
from andes.core.var import ExtState, Algeb, ExtAlgeb
from andes.core.model import ModelData, Model

class COI2Data(ModelData):
    """COI parameter data"""

    def __init__(self):
        ModelData.__init__(self)


class COI2Model(Model):
    """
    Implementation of COI.
    Added VSG int COI calculation.

    To understand this model, please refer to
    :py:class:`andes.core.service.NumReduce`,
    :py:class:`andes.core.service.NumRepeat`,
    :py:class:`andes.core.service.IdxFlatten`, and
    :py:class:`andes.core.service.BackRef`.
    """
    def __init__(self, system, config):
        Model.__init__(self, system, config)
        self.group = 'Calculation'
        self.flags.update({'tds': True})

        COIModelName = ["SynGen", "REGCVSG"]

        for RefModelName in COIModelName:

            RefModel = BackRef(info='Back reference to RefModel idx')
            setattr(self, "{}".format(RefModelName), RefModel)

            Idx = RefFlatten(ref=getattr(self, RefModelName))
            setattr(self, "Idx{}".format(RefModelName), Idx)

            M = ExtParam(model=RefModelName, src='M',
                         indexer=getattr(self, 'Idx'+RefModelName), export=False,
                         info='Linearly stored '+'RefModelName'+'.M',
                         )
            setattr(self, "M{}".format(RefModelName), M)

            wgen = ExtState(model=RefModelName,
                            src='omega',
                            indexer=getattr(self, 'Idx'+RefModelName),
                            tex_name=r'\omega_{gen}',
                            info='Linearly stored SynGen.omega',
                            )
            setattr(self, "wgen{}".format(RefModelName), wgen)

            agen = ExtState(model='SynGen',
                            src='delta',
                            indexer=self.SynGenIdx,
                            tex_name=r'\delta_{gen}',
                            info='Linearly stored SynGen.delta',
                            )
        self.d0 = ExtService(model='SynGen',
                             src='delta',
                             indexer=self.SynGenIdx,
                             tex_name=r'\delta_{gen,0}',
                             info='Linearly stored initial delta',
                             )

        self.a0 = ExtService(model='SynGen',
                             src='omega',
                             indexer=self.SynGenIdx,
                             tex_name=r'\omega_{gen,0}',
                             info='Linearly stored initial omega',
                             )

        self.Mt = NumReduce(u=self.M,
                            tex_name='M_t',
                            fun=np.sum,
                            ref=self.SynGen,
                            info='Summation of M by COI index',
                            )

        self.Mr = NumRepeat(u=self.Mt,
                            tex_name='M_{tr}',
                            ref=self.SynGen,
                            info='Repeated summation of M',
                            )

        self.Mw = ConstService(tex_name='M_w',
                               info='Inertia weights',
                               v_str='M/Mr')

        self.d0w = ConstService(tex_name=r'\delta_{gen,0,w}',
                                v_str='d0 * Mw',
                                info='Linearly stored weighted delta')

        self.a0w = ConstService(tex_name=r'\omega_{gen,0,w}',
                                v_str='a0 * Mw',
                                info='Linearly stored weighted omega')

        self.d0a = NumReduce(u=self.d0w,
                             tex_name=r'\delta_{gen,0,avg}',
                             fun=np.sum,
                             ref=self.SynGen,
                             info='Average initial delta',
                             cache=False,
                             )

        self.a0a = NumReduce(u=self.a0w,
                             tex_name=r'\omega_{gen,0,avg}',
                             fun=np.sum,
                             ref=self.SynGen,
                             info='Average initial omega',
                             cache=False,
                             )

        self.pidx = IdxRepeat(u=self.idx, ref=self.SynGen, info='Repeated COI.idx')

        # Note:
        # Even if d(omega) /d (omega) = 1, it is still stored as a lambda function.
        # When no SynGen is referencing any COI, j_update will not be called,
        # and Jacobian will become singular. `diag_eps = True` needs to be used.

        # Note:
        # Do not assign `v_str=1` for `omega`. Otherwise, COIs with no connected generators will
        # fail to initialize.
        self.omega = Algeb(tex_name=r'\omega_{coi}',
                           info='COI speed',
                           v_str='a0a',
                           v_setter=True,
                           e_str='-omega',
                           diag_eps=True,
                           )
        self.delta = Algeb(tex_name=r'\delta_{coi}',
                           info='COI rotor angle',
                           v_str='d0a',
                           v_setter=True,
                           e_str='-delta',
                           diag_eps=True,
                           )

        # Note:
        # `omega_sub` or `delta_sub` must not provide `v_str`.
        # Otherwise, values will be incorrectly summed for `omega` and `delta`.
        self.omega_sub = ExtAlgeb(model='COI',
                                  src='omega',
                                  e_str='Mw * wgen',
                                  indexer=self.pidx,
                                  info='COI frequency contribution of each generator'
                                  )
        self.delta_sub = ExtAlgeb(model='COI',
                                  src='delta',
                                  e_str='Mw * agen',
                                  indexer=self.pidx,
                                  info='COI angle contribution of each generator'
                                  )
    ###

        self.REGCVSGVSG = BackRef(info='Back reference to VSG idx')

        self.REGCVSGVSGIdx = RefFlatten(ref=self.REGCVSGVSG)

        self.M2 = ExtParam(model='REGCVSGVSG', src='M',
                          indexer=self.REGCVSGVSGIdx, export=False,
                          info='Linearly stored REGCVSGVSG.M',
                          )

        self.wgen2 = ExtState(model='REGCVSGVSG',
                             src='omega',
                             indexer=self.REGCVSGVSGIdx,
                             tex_name=r'\omega_{gen}',
                             info='Linearly stored SynGen.omega',
                             )
        self.agen2 = ExtState(model='REGCVSGVSG',
                             src='delta',
                             indexer=self.REGCVSGVSGIdx,
                             tex_name=r'\delta_{gen}',
                             info='Linearly stored REGCVSGVSG.delta',
                             )
        self.d02 = ExtService(model='REGCVSGVSG',
                             src='delta',
                             indexer=self.REGCVSGVSGIdx,
                             tex_name=r'\delta_{gen,0}',
                             info='Linearly stored initial delta',
                             )

        self.a02 = ExtService(model='REGCVSGVSG',
                             src='omega',
                             indexer=self.REGCVSGVSGIdx,
                             tex_name=r'\omega_{gen,0}',
                             info='Linearly stored initial omega',
                             )

        self.Mt = NumReduce(u=self.M,
                            tex_name='M_t',
                            fun=np.sum,
                            ref=self.SynGen,
                            info='Summation of M by COI index',
                            )

        self.Mr = NumRepeat(u=self.Mt,
                            tex_name='M_{tr}',
                            ref=self.SynGen,
                            info='Repeated summation of M',
                            )

        self.Mw = ConstService(tex_name='M_w',
                               info='Inertia weights',
                               v_str='M/Mr')

        self.d0w = ConstService(tex_name=r'\delta_{gen,0,w}',
                                v_str='d0 * Mw',
                                info='Linearly stored weighted delta')

        self.a0w = ConstService(tex_name=r'\omega_{gen,0,w}',
                                v_str='a0 * Mw',
                                info='Linearly stored weighted omega')

        self.d0a = NumReduce(u=self.d0w,
                             tex_name=r'\delta_{gen,0,avg}',
                             fun=np.sum,
                             ref=self.SynGen,
                             info='Average initial delta',
                             cache=False,
                             )

        self.a0a = NumReduce(u=self.a0w,
                             tex_name=r'\omega_{gen,0,avg}',
                             fun=np.sum,
                             ref=self.SynGen,
                             info='Average initial omega',
                             cache=False,
                             )

        self.pidx = IdxRepeat(u=self.idx, ref=self.SynGen, info='Repeated COI.idx')

        # Note:
        # Even if d(omega) /d (omega) = 1, it is still stored as a lambda function.
        # When no SynGen is referencing any COI, j_update will not be called,
        # and Jacobian will become singular. `diag_eps = True` needs to be used.

        # Note:
        # Do not assign `v_str=1` for `omega`. Otherwise, COIs with no connected generators will
        # fail to initialize.
        self.omega = Algeb(tex_name=r'\omega_{coi}',
                           info='COI speed',
                           v_str='a0a',
                           v_setter=True,
                           e_str='-omega',
                           diag_eps=True,
                           )
        self.delta = Algeb(tex_name=r'\delta_{coi}',
                           info='COI rotor angle',
                           v_str='d0a',
                           v_setter=True,
                           e_str='-delta',
                           diag_eps=True,
                           )

    def set_in_use(self):
        """
        Set the ``Model.in_use`` flag based on ``len(self.SynGenIdx.v)``.
        """
        self.in_use = (len(self.SynGenIdx.v) > 0)


class COI2(COI2Data, COI2Model):
    """
    Center of inertia calculation class.
    """

    def __init__(self, system, config):
        COI2Data.__init__(self)
        COI2Model.__init__(self, system, config)