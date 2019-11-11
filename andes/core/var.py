from typing import Optional, Union, List

import numpy as np
from andes.core.param import DataParam
from numpy import ndarray


class VarBase(object):
    """
    Base variable class

    This class can be used to instantiate a variable as
    an attribute of a model class.

    Parameters
    ----------
    name : str, optional
        Variable name
    info : str, optional
        Descriptive information
    unit : str, optional
        Unit
    tex_name : str
        LaTeX-formatted variable name. If is None, use `name`
        instead.

    Attributes
    ----------
    a : array-like
        variable address
    v : array-like
        local-storage of the variable value
    e : array-like
        local-storage of the corresponding equation value
    e_symbolic : str
        the string/symbolic representation of the equation
    e_lambdify : Callable
        SymPy-generated callable to update equation value;
        not intended to be provided by user
    """
    def __init__(self,
                 name: Optional[str] = None,
                 tex_name: Optional[str] = None,
                 info: Optional[str] = None,
                 unit: Optional[str] = None,
                 setter: Optional[bool] = False,
                 **kwargs
                 ):

        self.name = name
        self.info = info
        self.unit = unit

        self.tex_name = tex_name if tex_name else name
        self.owner = None
        self.id = None

        self.n = 0
        self.a: Optional[Union[ndarray, List]] = None
        self.v: Optional[ndarray] = None
        self.e: Optional[ndarray] = None

        self.v_init = None
        self.v_setter = setter

        self.e_symbolic = None
        self.e_lambdify = None

    def set_address(self, addr):
        """
        Set the address of this variables

        Parameters
        ----------
        addr : array-like
            The assigned address for this variable
        """
        self.a = addr
        self.n = len(self.a)
        self.v = np.zeros(self.n)
        self.e = np.zeros(self.n)

    def get_name(self):
        return [self.name]


class Algeb(VarBase):
    """
    Algebraic variable class, an alias of the `VarBase`.

    Attributes
    ----------
    e_code : str
        Equation code string, equals string literal ``g``
    v_code : str
        Variable code string, equals string literal ``y``
    """
    e_code = 'g'
    v_code = 'y'


class State(VarBase):
    """
    Differential variable class, an alias of the `VarBase`.

    Attributes
    ----------
    e_code : str
        Equation code string, equals string literal ``f``
    v_code : str
        Variable code string, equals string literal ``x``
    """
    e_code = 'f'
    v_code = 'x'


class Calc(VarBase):
    """
    Calculated variable class, an alias of the `VarBase`.

    This class is meant for internally calculated variables
    such as line flow power.

    Warnings
    --------
    Not implemented yet..
    """
    pass


class ExtVar(VarBase):
    """
    Externally defined algebraic variable

    This class is used to retrieve the addresses of externally-
    defined variable. The `e` value of the `ExtVar` will be added
    to the corresponding address in the DAE equation.

    Parameters
    ----------
    model : str
        Name of the source model
    src : str
        Source variable name
    indexer : ParamBase
        A parameter of the hosting model, used as indices into
        the source model and variable. If is None, the source
        variable address will be fully copied.

    Attributes
    ----------
    parent_model : Model
        The parent model providing the original parameter.
    parent_instance : ParamBase
        The parent parameter, which is an attribute of the parent
        model, providing the original values.
    uid : array-like
        An array containing the absolute indices into the
        parent_instance values.
    e_code : str
        Equation code string; copied from the parent instance.
    v_code : str
        Variable code string; copied from the parent instance.
    """
    def __init__(self,
                 model: str,
                 src: str,
                 indexer: Optional[Union[List, ndarray, DataParam]] = None,
                 *args,
                 **kwargs):
        super(ExtVar, self).__init__(*args, **kwargs)
        self.initialized = False
        self.model = model
        self.src = src
        self.indexer = indexer

        self.parent_model = None
        self.parent_instance = None
        self.uid = None

    def link_external(self, ext_model):
        """
        Update variable addresses provided by external models

        This method sets attributes including `parent_model`,
        `parent_instance`, `uid`, `a`, `n`, `e_code` and
        `v_code`. It initializes the `e` and `v` to zero.

        Returns
        -------
        None

        Parameters
        ----------
        ext_model : Model
            Instance of the parent model
        """
        self.parent_model = ext_model
        self.parent_instance = ext_model.__dict__[self.src]

        if self.indexer is not None:
            self.uid = ext_model.idx2uid(self.indexer.v)
        else:
            self.uid = np.arange(ext_model.n, dtype=int)

        self.n = len(self.uid)

        # set initial v and e values to zero
        self.v = np.zeros(self.n)
        self.e = np.zeros(self.n)

        if self.n != 0:
            self.a = self.parent_instance.a[self.uid]
        else:
            self.a = np.array([])


class ExtState(ExtVar):
    e_code = 'f'
    v_code = 'x'


class ExtAlgeb(ExtVar):
    e_code = 'g'
    v_code = 'y'
