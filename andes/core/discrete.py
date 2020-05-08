import logging
from typing import Optional, Union, Tuple, List
from andes.shared import np
from andes.utils.func import interp_n2

logger = logging.getLogger(__name__)


class Discrete(object):
    """
    Base discrete class.

    Discrete classes export flag arrays (usually boolean) .
    """

    def __init__(self, name=None, tex_name=None, info=None):
        self.name = name
        self.tex_name = tex_name
        self.info = info
        self.owner = None
        self.export_flags = []
        self.export_flags_tex = []
        self.x_set = list()
        self.y_set = list()  # NOT being used

    def check_var(self, *args, **kwargs):
        """
        This function is called in ``l_update_var`` before evaluating equations.

        It should update internal flags only.
        """
        pass

    def check_eq(self):
        """
        This function is called in ``l_check_eq`` after updating equations.

        It should update internal flags only.
        """
        pass

    def set_eq(self):
        """
        This function is used exclusively by AntiWindup for appending equations and values to ``x_set``.

        It is called after ``check_eq``.
        """
        pass

    def get_names(self):
        """
        Available symbols from this class

        Returns
        -------

        """
        return [f'{self.name}_{flag}' for flag in self.export_flags]

    def get_tex_names(self):
        """
        Return tex_names of exported flags.

        TODO: Fix the bug described in the warning below.

        Warnings
        --------
        If underscore `_` appears in both flag tex_name and `self.tex_name` (for example, when this discrete is
        within a block), the exported tex_name will become invalid for SymPy.
        Variable name substitution will fail.

        Returns
        -------
        list
            A list of tex_names for all exported flags.
        """

        return [rf'{flag_tex}^{self.tex_name}' for flag_tex in self.export_flags_tex]

    def get_values(self):
        return [self.__dict__[flag] for flag in self.export_flags]

    @property
    def class_name(self):
        return self.__class__.__name__

    def list2array(self, n):
        for flag in self.export_flags:
            self.__dict__[flag] = self.__dict__[flag] * np.ones(n)


class LessThan(Discrete):
    """
    Less than (<) comparison function.

    Exports two flags: z1 and z0.
    For elements satisfying the less-than condition, the corresponding z1 = 1.
    z0 is the element-wise negation of z1.

    Notes
    -----
    The default z0 and z1, if not enabled, can be set through the constructor.
    """
    def __init__(self, u, bound, equal=False, enable=True, name=None, tex_name=None, cache=False,
                 z0=0, z1=1):
        super().__init__(name=name, tex_name=tex_name)
        self.u = u
        self.bound = bound
        self.equal: bool = equal
        self.enable: bool = enable
        self.cache: bool = cache
        self._eval: bool = False  # if has been eval'ed and cached

        self.z0 = np.array([z0])  # negation of `self.z1`
        self.z1 = np.array([z1])  # if the less-than condition (u < bound) is True
        self.export_flags = ['z0', 'z1']
        self.export_flags_tex = ['z_0', 'z_1']

    def check_var(self, *args, **kwargs):
        """
        If enabled, set flags based on inputs. Use cached values if enabled.
        """
        if not self.enable:
            return
        if self.cache and self._eval:
            return

        if not self.equal:
            self.z1[:] = np.less(self.u.v, self.bound.v)
        else:
            self.z1[:] = np.less_equal(self.u.v, self.bound.v)

        self.z0[:] = np.logical_not(self.z1)

        self._eval = True


class Limiter(Discrete):
    """
    Base limiter class.

    This class compares values and sets limit values. Exported flags are `zi`, `zl` and `zu`.

    Notes
    -----
    If not enabled, the default flags are ``zu = zl = 0``, ``zi = 1``.

    Parameters
    ----------
    u : BaseVar
        Input Variable instance
    lower : BaseParam
        Parameter instance for the lower limit
    upper : BaseParam
        Parameter instance for the upper limit
    upper_only : bool
        True to only use the upper limit
    lower_only : bool
        True to only use the lower limit

    Attributes
    ----------
    zl : array-like
        Flags of elements violating the lower limit;
        A array of zeros and/or ones.
    zi : array-like
        Flags for within the limits
    zu : array-like
        Flags for violating the upper limit
    """

    def __init__(self, u, lower, upper, enable=True, name=None, tex_name=None, info=None,
                 lower_only=False, upper_only=False):
        super().__init__(name=name, tex_name=tex_name, info=info)
        self.u = u
        self.lower = lower
        self.upper = upper
        self.enable = enable
        self.lower_only = lower_only
        self.upper_only = upper_only

        self.zu = np.array([0])
        self.zl = np.array([0])
        self.zi = np.array([1])

        self.export_flags = ['zi']
        self.export_flags_tex = ['z_i']

        if not self.upper_only:
            self.export_flags.append('zl')
            self.export_flags_tex.append('z_l')
        if not self.lower_only:
            self.export_flags.append('zu')
            self.export_flags_tex.append('z_u')

    def check_var(self, *args, **kwargs):
        """
        Evaluate the flags.
        """
        if not self.enable:
            return

        if not self.lower_only:
            self.zu[:] = np.greater_equal(self.u.v, self.upper.v)
        if not self.upper_only:
            self.zl[:] = np.less_equal(self.u.v, self.lower.v)

        self.zi[:] = np.logical_not(np.logical_or(self.zu, self.zl))


class SortedLimiter(Limiter):
    """
    A comparer with the top value selection.

    """

    def __init__(self, u, lower, upper, enable=True,
                 n_select: Optional[int] = None, name=None, tex_name=None):

        super().__init__(u, lower, upper, enable=enable, name=name, tex_name=tex_name)
        self.n_select = int(n_select) if n_select else 0

    def check_var(self, *args, **kwargs):
        if not self.enable:
            return
        super().check_var()

        if self.n_select is not None and self.n_select > 0:
            asc = np.argsort(self.u.v - self.lower.v)   # ascending order
            desc = np.argsort(self.upper.v - self.u.v)

            lowest_n = asc[:self.n_select]
            highest_n = desc[:self.n_select]

            reset_in = np.ones(self.u.v.shape)
            reset_in[lowest_n] = 0
            reset_in[highest_n] = 0
            reset_out = 1 - reset_in

            self.zi[:] = np.logical_or(reset_in, self.zi)
            self.zl[:] = np.logical_and(reset_out, self.zl)
            self.zu[:] = np.logical_and(reset_out, self.zu)


class HardLimiter(Limiter):
    """
    Hard limiter for algebraic or differential variable. This class is an alias of `Limiter`.
    """
    pass


class AntiWindup(Limiter):
    """
    Anti-windup limiter.

    Anti-windup limiter prevents the wind-up effect of a differential variable.
    The derivative of the differential variable is reset if it continues to increase in the same direction
    after exceeding the limits.
    During the derivative return, the limiter will be inactive ::

        if x > xmax and x dot > 0: x = xmax and x dot = 0
        if x < xmin and x dot < 0: x = xmin and x dot = 0

    This class takes one more optional parameter for specifying the equation.

    Parameters
    ----------
    state : State, ExtState
        A State (or ExtState) whose equation value will be checked and, when condition satisfies, will be reset
        by the anti-windup-limiter.
    """

    def __init__(self, u, lower, upper, enable=True, name=None, tex_name=None, state=None):
        super().__init__(u, lower, upper, enable=enable, name=name, tex_name=tex_name)
        self.state = state if state else u

    def check_var(self, *args, **kwargs):
        """
        This function is empty. Defers `check_var` to `check_eq`.
        """
        pass

    def check_eq(self):
        """
        Check the variables and equations and set the limiter flags.
        """
        self.zu[:] = np.logical_and(np.greater_equal(self.u.v, self.upper.v),
                                    np.greater_equal(self.state.e, 0))
        self.zl[:] = np.logical_and(np.less_equal(self.u.v, self.lower.v),
                                    np.less_equal(self.state.e, 0))
        self.zi[:] = np.logical_not(np.logical_or(self.zu, self.zl))

    def set_eq(self):
        """
        Reset differential equation values based on limiter flags.

        Notes
        -----
        The current implementation reallocates memory for `self.x_set` in each call.
        Consider improving for speed. (TODO)
        """

        # must flush the `x_set` list at the beginning
        self.x_set = list()

        if not np.all(self.zi):
            idx = np.where(self.zi == 0)
            self.state.e[:] = self.state.e * self.zi
            self.state.v[:] = self.state.v * self.zi + self.upper.v * self.zu + self.lower.v * self.zl
            self.x_set.append((self.state.a[idx], self.state.v[idx]))
            # logger.debug(f'AntiWindup for states {self.state.a[idx]}')

        # Very important note:
        # `System.fg_to_dae` is called after `System.l_update_eq`, which calls this function.
        # Equation values set in `self.state.e` is collected by `System._e_to_dae`, while
        # variable values are collected by the separate loop in `System.fg_to_dae`.
        # Also, equation values are processed in `TDS` for resetting the `q`.


class Selector(Discrete):
    """
    Selection of variables using the provided reduce function.

    The reduce function should take the given number of arguments. An example function is `np.maximum.reduce`
    which can be used to select the maximum.

    Names are in `s0`, `s1`, ... and `sn`

    Warnings
    --------
    A potential bug when more than two inputs are provided, and values in different inputs are equal.
    FIXME: More than one flag will se true in this case.

    Examples
    --------
    Example 1: select the largest value between `v0` and `v1` and put it into vmax.

    After the definitions of `v0` and `v1`, define the algebraic variable `vmax` for the largest value,
    and a selector `vs` ::

        self.vmax = Algeb(v_str='maximum(v0, v1) - vmax',
                          tex_name='v_{max}',
                          e_str='vs_s0 * v0 + vs_s1 * v1 - vmax')

        self.vs = Selector(self.v0, self.v1, fun=np.maximum.reduce)

    The initial value of `vmax` is calculated by ``maximum(v0, v1)``, which is the element-wise maximum in SymPy
    and will be generated into ``np.maximum(v0, v1)``. The equation of `vmax` is to select the values based on
    `vs_s0` and `vs_s1`.

    Notes
    -----
    A common pitfall is the 0-based indexing in the Selector flags. Note that exported flags start from 0. Namely,
    `s0` corresponds to the first variable provided for the Selector constructor.

    See Also
    --------
    numpy.ufunc.reduce : NumPy reduce function
    """
    def __init__(self, *args, fun, tex_name=None):
        super().__init__(tex_name=tex_name)
        self.input_vars = args
        self.fun = fun
        self.n = len(args)
        self._s = [0] * self.n
        self._inputs = None
        self._outputs = None

        for i in range(len(self.input_vars)):
            self.__dict__[f's{i}'] = 0

        self.export_flags = [f's{i}' for i in range(len(self.input_vars))]
        self.export_flags_tex = [f's_{i}' for i in range(len(self.input_vars))]

    def check_var(self, *args, **kwargs):
        """
        Set the i-th variable's flags to 1 if the return of the reduce function equals the i-th input.
        """
        self._inputs = [self.input_vars[i].v for i in range(self.n)]
        self._outputs = self.fun(self._inputs)
        for i in range(self.n):
            self.__dict__[f's{i}'][:] = np.equal(self._inputs[i], self._outputs)


class Switcher(Discrete):
    """
    Switcher based on an input parameter.

    The switch class takes one v-provider, compares the input with each value in the option list, and exports
    one flag array for each option. The flags are 0-indexed.

    Exported flags are named with `_s0`, `_s1`, ..., with a total number of `len(options)`. See the examples
    section.

    Notes
    -----
    Switches needs to be distinguished from Selector.

    Switcher is for generating flags indicating option selection based on an input parameter. Selector is
    for generating flags at run time based on variable values and a selection function.

    Examples
    --------
    The IEEEST model takes an input for selecting the signal. Options are 1 through 6.
    One can construct ::

        self.IC = NumParam(info='input code 1-6')  # input code
        self.SW = Switcher(u=self.IC, options=[1, 2, 3, 4, 5, 6])

    If the IC values from the data file ends up being ::

        self.IC.v = np.array([1, 2, 2, 4, 6])

    Then, the exported flag arrays will be ::

        {'IC_s0': np.array([1, 0, 0, 0, 0]),
         'IC_s1': np.array([0, 1, 1, 0, 0]),
         'IC_s2': np.array([0, 0, 0, 0, 0]),
         'IC_s3': np.array([0, 0, 0, 1, 0]),
         'IC_s4': np.array([0, 0, 0, 0, 0]),
         'IC_s5': np.array([0, 0, 0, 0, 1])
        }
    """

    def __init__(self, u, options: Union[list, Tuple], name: str = None, tex_name: str = None, cache=True):
        super().__init__(name=name, tex_name=tex_name)
        self.u = u
        self.options: Union[List, Tuple] = options
        self.cache: bool = cache
        self._eval: bool = False  # if the flags has been evaluated

        for i in range(len(options)):
            self.__dict__[f's{i}'] = 0

        self.export_flags = [f's{i}' for i in range(len(options))]
        self.export_flags_tex = [f's_{i}' for i in range(len(options))]

    def check_var(self, *args, **kwargs):
        """
        Set the switcher flags based on inputs. Uses cached flags if cache is set to True.

        TODO: check if all inputs are valid
        """
        if self.cache and self._eval:
            return

        for v in self.u.v:
            if v not in self.options:
                raise ValueError(f'option {v} is invalid for {self.owner.class_name}.{self.u.name}. '
                                 f'Options are {self.options}.')
        for i in range(len(self.options)):
            self.__dict__[f's{i}'][:] = np.equal(self.u.v, self.options[i])

        self._eval = True

    def list2array(self, n):
        """
        This forces to evaluate Switcher upon System setup
        """
        super().list2array(n)
        self.check_var()


class DeadBand(Limiter):
    r"""
    Dead band with the direction of return.

    Parameters
    ----------
    u : NumParam
        The pre-deadband input variable
    center : NumParam
        Neutral value of the output
    lower : NumParam
        Lower bound
    upper : NumParam
        Upper bpund
    enable : bool
        Enabled if True; Disabled and works as a pass-through if False.

    Notes
    -----

    Input changes within a deadband will incur no output changes. This component computes and exports five flags.

    Three flags computed from the current input:
     - zl: True if the input is below the lower threshold
     - zi: True if the input is within the deadband
     - zu: True if is above the lower threshold

    Two flags indicating the direction of return:
     - zur: True if the input is/has been within the deadband and was returned from the upper threshold
     - zlr: True if the input is/has been within the deadband and was returned from the lower threshold

    Initial condition:

    All five flags are initialized to zero. All flags are updated during `check_var` when enabled. If the
    deadband component is not enabled, all of them will remain zero.

    Examples
    --------

    Exported deadband flags need to be used in the algebraic equation corresponding to the post-deadband variable.
    Assume the pre-deadband input variable is `var_in` and the post-deadband variable is `var_out`. First, define a
    deadband instance `db` in the model using ::

        self.db = DeadBand(u=self.var_in,
                           center=self.dbc,
                           lower=self.dbl,
                           upper=self.dbu)

    To implement a no-memory deadband whose output returns to center when the input is within the band,
    the equation for `var` can be written as ::

        var_out.e_str = 'var_in * (1 - db_zi) + \
                         (dbc * db_zi) - var_out'

    To implement a deadband whose output is pegged at the nearest deadband bounds, the equation for `var` can be
    provided as ::

        var_out.e_str = 'var_in * (1 - db_zi) + \
                         dbl * db_zlr + \
                         dbu * db_zur - var_out'

    """
    def __init__(self, u, center, lower, upper, enable=True):
        """

        """
        super().__init__(u, lower, upper, enable=enable)
        self.center = center

        # default state if not enabled
        self.zi = np.array([0.])
        self.zl = np.array([0.])
        self.zu = np.array([0.])
        self.zur = np.array([0.])
        self.zlr = np.array([0.])

        self.export_flags = ['zl', 'zi', 'zu', 'zur', 'zlr']
        self.export_flags_tex = ['z_l', 'z_i', 'z_u', 'z_ur', 'z_lr']

    def check_var(self, *args, **kwargs):
        """
        Notes
        -----

        Updates five flags: zi, zu, zl; zur, and zlr based on the following rules:

        zu:
          1 if u > upper; 0 otherwise.

        zl:
          1 if u < lower; 0 otherwise.

        zi:
          not(zu or zl);

        zur:
         - set to 1 when (previous zu + present zi == 2)
         - hold when (previous zi == zi)
         - clear otherwise

        zlr:
         - set to 1 when (previous zl + present zi == 2)
         - hold when (previous zi == zi)
         - clear otherwise
        """
        if not self.enable:
            return
        zu = np.greater(self.u.v, self.upper.v)
        zl = np.less(self.u.v, self.lower.v)
        zi = np.logical_not(np.logical_or(zu, zl))

        # square return dead band
        self.zur[:] = np.equal(self.zu + zi, 2) + self.zur * np.equal(zi, self.zi)
        self.zlr[:] = np.equal(self.zl + zi, 2) + self.zlr * np.equal(zi, self.zi)


class Delay(Discrete):
    """
    Delay class to memorize past variable values.

    TODO: Add documentation.
    """

    def __init__(self, u, mode='step', delay=0, name=None, tex_name=None, info=None):
        Discrete.__init__(self, name=name, tex_name=tex_name, info=info)

        if mode not in ('step', 'time'):
            raise ValueError(f'mode {mode} is invalid. Must be in "step" or "time"')

        self.u = u
        self.mode = mode
        self.delay = delay
        self.export_flags = ['v']
        self.export_flags_tex = ['v']

        self.t = np.array([0])
        self.v = np.array([0])
        self._v_mem = np.zeros((0, 1))
        self.rewind = False

    def list2array(self, n):
        """
        Allocate memory for storage arrays.
        """
        super().list2array(n)
        if self.mode == 'step':
            self._v_mem = np.zeros((n, self.delay + 1))
            self.t = np.zeros(self.delay + 1)
        else:
            self._v_mem = np.zeros((n, 1))

    def check_var(self, dae_t, *args, **kwargs):

        # Storage:
        # Output values is in the first col.
        # Latest values are stored in /appended to the last column
        self.rewind = False

        if dae_t == 0:
            self._v_mem[:] = self.u.v[:, None]

        elif dae_t < self.t[-1]:
            self.rewind = True
            self.t[-1] = dae_t
            self._v_mem[:, -1] = self.u.v

        elif dae_t == self.t[-1]:
            self._v_mem[:, -1] = self.u.v

        elif dae_t > self.t[-1]:
            if self.mode == 'step':
                self.t[:-1] = self.t[1:]
                self.t[-1] = dae_t

                self._v_mem[:, :-1] = self._v_mem[:, 1:]
                self._v_mem[:, -1] = self.u.v
            else:
                self.t = np.append(self.t, dae_t)
                self._v_mem = np.hstack((self._v_mem, self.u.v[:, None]))

                if dae_t - self.t[0] > self.delay:
                    t_interp = dae_t - self.delay
                    idx = np.argmax(self.t >= t_interp) - 1
                    v_interp = interp_n2(t_interp,
                                         self.t[idx:idx+2],
                                         self._v_mem[:, idx:idx + 2])

                    self.t[idx] = t_interp
                    self._v_mem[:, idx] = v_interp

                    self.t = np.delete(self.t, np.arange(0, idx))
                    self._v_mem = np.delete(self._v_mem, np.arange(0, idx), axis=1)

        self.v[:] = self._v_mem[:, 0]

    def __repr__(self):
        out = ''
        out += f'v:\n {self.v}\n'
        out += f't:\n {self.t}\n'
        out += f'_v_men: \n {self._v_mem}\n'
        return out


class Average(Delay):
    """
    Compute the average of a BaseVar over a period of time or a number of samples.
    """
    def check_var(self, dae_t, *args, **kwargs):
        Delay.check_var(self, dae_t, *args, **kwargs)

        if dae_t == 0:
            self.v[:] = self._v_mem[:, -1]
            self._v_mem[:, :-1] = 0
            return
        else:
            nt = len(self.t)
            self.v[:] = 0.5 * np.sum((self._v_mem[:, 1-nt:] + self._v_mem[:, -nt:-1]) *
                                     (self.t[1:] - self.t[:-1]), axis=1) / (self.t[-1] - self.t[0])


class Derivative(Delay):
    """
    Compute the derivative of an algebraic variable using numerical differentiation.
    """
    def __init__(self, u, name=None, tex_name=None, info=None):
        Delay.__init__(self, u=u, mode='step', delay=1,
                       name=name, tex_name=tex_name, info=info)

    def check_var(self, dae_t, *args, **kwargs):
        Delay.check_var(self, dae_t, *args, **kwargs)

        # Note:
        #    Very small derivatives (< 1e-8) could cause numerical problems (chattering).
        #    Need to reset the output to zero following a rewind.
        if (dae_t == 0) or (self.rewind is True):
            self.v[:] = 0
        else:
            self.v[:] = (self._v_mem[:, 1] - self._v_mem[:, 0]) / (self.t[1] - self.t[0])
            self.v[np.where(self.v < 1e-8)] = 0
