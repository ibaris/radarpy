from __future__ import division

import inspect

import numpy as np

import util as util
from respy.unit_base.convert import convert_to_unit
from respy.unit_base.operations import compute_logical_operation, compute_bitwise_operation, compute_operation
from respy.unit_base.auxil import decompose_expr_to_atoms
from respy.units.auxil import __NONE_UNITS__, __OPERATORS__, __UFUNC_NAME__
from respy.units.util import Zero, One
from respy.unit_base.auxil import get_unit

np.seterr(divide='ignore', invalid='ignore')


class Quantity(np.ndarray):
    def __new__(cls, value, unit=None, dtype=None, copy=True, order=None,
                subok=False, ndmin=0, name=None, constant=False):
        """
        The Quantity object is meant to represent a value that has some unit associated with the number.

        Parameters
        ----------
        value : float, int, numpy.ndarray, sympy.core.all_classes
            The numerical value of this quantity in the units given by unit.

        unit : sympy.physics.units.quantities.Quantity, str
            An object that represents the unit associated with the input value.
            Must be an `sympy.physics.units.quantities.Quantity` object or a string parsable by
            the :mod:`~respy.units` package.

        dtype : numpy.dtype, type, int, float, double, optional
            The dtype of the resulting Numpy array or scalar that will
            hold the value.  If not provided, it is determined from the input,
            except that any input that cannot represent float (integer and bool)
            is converted to float.

        copy : bool, optional
            If `True` (default), then the value is copied.  Otherwise, a copy will
            only be made if ``__array__`` returns a copy, if value is a nested
            sequence, or if a copy is needed to satisfy an explicitly given
            ``dtype``.  (The `False` option is intended mostly for internal use,
            to speed up initialization where a copy is known to have been made.
            Use with care.)

        order : {'C', 'F', 'A'}, optional
            Specify the order of the array.  As in `~numpy.array`.  This parameter
            is ignored if the input is a `Quantity` and ``copy=False``.

        subok : bool, optional
            If `False` (default), the returned array will be forced to be a
            `Quantity`.

        ndmin : int, optional
            Specifies the minimum number of dimensions that the resulting array
            should have.  Ones will be pre-pended to the shape as needed to meet
            this requirement.  This parameter is ignored if the input is a
            `Quantity` and ``copy=False``.
        name : str
            A name for the created Quantity.
        constant : bool
            If True and the constant has a name the name will be replaced after a operation.

        Attributes
        ----------
        value : np.ndarray
            The numerical value of this quantity in the units given by unit.
        unit : sympy.physics.units.quantities.Quantity
            An object that represents the unit associated with the input value.
        dtype : type
            The data type of the value
        copy: bool
            The entered copy bool value.
        order : str
            Order of the array.
        subok : bool
            The entered subok value.
        ndmin : int
            Minimum number of dimensions
        name : str
            Name of the Quantity
        constant : bool
            Information about if the Quantity is an constant or not.
        unitstr : str
            Parameter unit as str.
        math_text : str
            Parameter unit as math text.
        label : str
            Parameter name and unit as math text.
        expr : np.ndarray
            The whole expression (value * unit) as sympy.core.mul.Mul.
        tolist : list
            Value and unit as a list.


        Methods
        -------
        decompose()
            Return value as np.ndarray and unit as sympy.physics.units.quantities.Quantity object.
        decompose_expr(expr)
            Extract value and unit from a sympy.core.mul.Mul object.
        set_name(name)
            Set a name for the current Quantity.
        convert_to(unit, inplace=True)
            Convert unit to another units.

        Raises
        ------
        UnitError
        DimensionError

        See Also
        --------
        respry.units.util.Units

        """

        x = np.array(value, dtype=dtype, copy=copy, order=order, subok=subok, ndmin=ndmin)
        x = np.atleast_1d(x)

        if x.dtype == int:
            dtype = np.double
            x = x.astype(dtype)
        else:
            pass

        obj = x.view(type=cls)

        if unit is None:
            obj.unit = Zero
            obj.dimension = Zero
        else:
            obj.unit = get_unit(unit)
            try:
                obj.dimension = obj.unit.dimension.name

            except AttributeError:
                obj.dimension = Zero

        obj.value = x
        obj._dtype = x.dtype

        if name is None:
            obj.name = b''
        else:
            obj.name = name

        obj.constant = constant

        obj.copy = copy
        obj.order = order
        obj.subok = subok
        obj.ndmin = ndmin
        obj.quantity = True

        return obj

    # --------------------------------------------------------------------------------------------------------
    # Magic Methods
    # --------------------------------------------------------------------------------------------------------
    def __repr__(self):
        prefix = '<{0} '.format(self.__class__.__name__)
        sep = ', '
        arrstr = np.array2string(self,
                                 separator=sep,
                                 prefix=prefix)

        if self.name is None or self.name is b'':
            return '{0}{1} [{2}]>'.format(prefix, arrstr, self.unitstr)

        else:
            return '{0}{1} {2} in [{3}]>'.format(prefix, arrstr, self.name, self.unitstr)

    def __array_finalize__(self, obj):
        # see InfoArray.__array_finalize__ for comments
        if obj is None:
            return
        else:
            self.unit = getattr(obj, 'unit', None)
            self.value = getattr(obj, 'value', None)
            self.name = getattr(obj, 'name', None)
            self.constant = getattr(obj, 'constant', None)
            self._dtype = getattr(obj, '_dtype', None)
            self.copy = getattr(obj, 'copy', None)
            self.order = getattr(obj, 'order', None)
            self.subok = getattr(obj, 'subok', None)
            self.ndmin = getattr(obj, 'ndmin', None)
            self.dimension = getattr(obj, 'dimension', None)
            self.quantity = getattr(obj, 'quantity', None)

    def __array_wrap__(self, out_arr, context=None):
        return np.ndarray.__array_wrap__(self, out_arr, context)

    # --------------------------------------------------------------------------------------------------------
    # Operator
    # --------------------------------------------------------------------------------------------------------
    # Attribute Operations -------------------------------------------------------------------------------
    def __getitem__(self, item):
        value = self.value[item]
        return self.__create_new_instance(value, self.unit, self.name)

    # Mathematical Operations ----------------------------------------------------------------------------
    # Left Operations -------------------------------------------------------------------------------
    def __mul__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        value, unit, dtype, name = compute_operation(self, other, operator, right_handed=False)

        if unit is None:
            unit = Zero

        return self.__create_new_instance(value, unit, name, dtype)

    def __truediv__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        value, unit, dtype, name = compute_operation(self, other, operator, right_handed=False)

        if unit is None:
            unit = Zero

        return self.__create_new_instance(value, unit, name, dtype)

    def __floordiv__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        value, unit, dtype, name = compute_operation(self, other, operator, right_handed=False)

        if unit is None:
            unit = Zero

        return self.__create_new_instance(value, unit, name, dtype)

    def __mod__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        value, unit, dtype, name = compute_operation(self, other, operator, right_handed=False)

        if unit is None:
            unit = Zero

        return self.__create_new_instance(value, unit, name, dtype)

    __div__ = __truediv__

    def __add__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        value, unit, dtype, name = compute_operation(self, other, operator, right_handed=False)

        if unit is None:
            unit = Zero

        return self.__create_new_instance(value, unit, name, dtype)

    def __sub__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        value, unit, dtype, name = compute_operation(self, other, operator, right_handed=False)

        if unit is None:
            unit = Zero

        return self.__create_new_instance(value, unit, name, dtype)

    def __pow__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        value, unit, dtype, name = compute_operation(self, other, operator, right_handed=False)

        if unit is None:
            unit = Zero

        return self.__create_new_instance(value, unit, name, dtype)

    def __lshift__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        return compute_bitwise_operation(self, other, operator, right_handed=False)

    def __rshift__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        return compute_bitwise_operation(self, other, operator, right_handed=False)

    def __and__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        return compute_bitwise_operation(self, other, operator, right_handed=False)

    def __or__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        return compute_bitwise_operation(self, other, operator, right_handed=False)

    def __xor__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        return compute_bitwise_operation(self, other, operator, right_handed=False)

    # Right Operations --------------------------------------------------------------------------------
    __rmul__ = __mul__
    __radd__ = __add__

    def __rtruediv__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        value, unit, dtype, name = compute_operation(self, other, operator, right_handed=True)

        if unit is None:
            unit = Zero

        return self.__create_new_instance(value, unit, name, dtype)

    __rdiv__ = __rtruediv__

    def __rsub__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        value, unit, dtype, name = compute_operation(self, other, operator, right_handed=True)

        if unit is None:
            unit = Zero

        return self.__create_new_instance(value, unit, name, dtype)

    def __rlshift__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        return compute_bitwise_operation(self, other, operator, right_handed=True)

    def __rrshift__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        return compute_bitwise_operation(self, other, operator, right_handed=True)

    def __rfloordiv__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        value, unit, dtype, name = compute_operation(self, other, operator, right_handed=True)

        return self.__create_new_instance(value, unit, name, dtype)

    def __rmod__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        return compute_bitwise_operation(self, other, operator, right_handed=True)

    def __rpow__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        return compute_bitwise_operation(self, other, operator, right_handed=True)

    def __rand__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        return compute_bitwise_operation(self, other, operator, right_handed=True)

    def __ror__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        return compute_bitwise_operation(self, other, operator, right_handed=True)

    def __rxor__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]

        return compute_bitwise_operation(self, other, operator, right_handed=True)

    # Augmented Assignment -------------------------------------------------------------------------------
    __iadd__ = __add__
    __isub__ = __sub__
    __imul__ = __mul__
    __ifloordiv__ = __floordiv__
    __idiv__ = __div__
    __itruediv__ = __truediv__
    __imod__ = __mod__
    __ipow__ = __pow__
    __ilshift__ = __lshift__
    __irshift__ = __rshift__
    __iand__ = __and__
    __ior__ = __or__
    __ixor__ = __xor__

    # --------------------------------------------------------------------------------------------------------
    #  Comparison
    # --------------------------------------------------------------------------------------------------------
    def __eq__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]
        return compute_logical_operation(self, other, operator)

    def __ne__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]
        return compute_logical_operation(self, other, operator)

    def __lt__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]
        return compute_logical_operation(self, other, operator)

    def __gt__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]
        return compute_logical_operation(self, other, operator)

    def __le__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]
        return compute_logical_operation(self, other, operator)

    def __ge__(self, other):
        other = self.__check_other(other)
        operator = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]
        return compute_logical_operation(self, other, operator)

    # --------------------------------------------------------------------------------------------------------
    # Numeric Magic Methods
    # --------------------------------------------------------------------------------------------------------
    def __pos__(self):
        name = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]
        OPERATOR = __OPERATORS__.get(name)

        value = OPERATOR(self.value)
        return self.__create_new_instance(value, self.unit, self.name)

    def __neg__(self):
        name = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]
        OPERATOR = __OPERATORS__.get(name)

        value = OPERATOR(self.value)
        return self.__create_new_instance(value, self.unit, self.name)

    def __abs__(self):
        name = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]
        OPERATOR = __OPERATORS__.get(name)

        value = OPERATOR(self.value)
        return self.__create_new_instance(value, self.unit, self.name)

    def __invert__(self):
        name = __UFUNC_NAME__[inspect.currentframe().f_code.co_name]
        OPERATOR = __OPERATORS__.get(name)

        value = OPERATOR(self.value)
        return self.__create_new_instance(value, self.unit, self.name)

    def __iter__(self):
        def iter_over_value(unit, name):
            for item in self.value:
                yield self.__create_new_instance(item, unit, name)

        return iter_over_value(self.unit, self.name)

    # --------------------------------------------------------------------------------------------------------
    # Properties
    # --------------------------------------------------------------------------------------------------------
    @property
    def real(self):
        return self.__create_new_instance(self.value.real, unit=self.unit, name=self.name, dtype=self.value.real.dtype)

    @property
    def imag(self):
        return self.__create_new_instance(self.value.imag, unit=self.unit, name=self.name, dtype=self.value.imag.dtype)

    @property
    def unitstr(self):
        """
        Return the unit of the expression as string.

        Returns
        -------
        unit : str
        """

        if self.unit in __NONE_UNITS__:
            return '-'
        else:
            return str(self.unit)

    @property
    def unit_mathstr(self):
        """
        Return the unit of the expression as math text of form r'$unit$'.

        Returns
        -------
        unit : str
        """

        if self.unit in __NONE_UNITS__:
            return '-'
        else:
            unit = r'$' + self.unitstr.replace('**', '^') + '$'

            return unit

    @property
    def label(self):
        """
        Return the name and the unit of the Quantity as math text.

        Returns
        -------
        label : str
        """

        return self.name + ' ' + '\n' + ' in ' + '[' + self.unit_mathstr + ']'

    @property
    def expr(self):
        """
        Return the expression.

        Returns
        -------
        expr : numpy.ndarray with sympy.core.mul.Mul
        """
        return self.value * self.unit

    @property
    def tolist(self):
        """
        Convert values and units to list.

        Returns
        -------
        tuple with two lists ([values], [units])
        """
        return self.value.tolist(), [self.unit]

    # --------------------------------------------------------------------------------------------------------
    # Callable Methods
    # --------------------------------------------------------------------------------------------------------
    def set_constant(self, constant):
        if isinstance(constant, bool):
            self.constant = constant
        else:
            raise ValueError("Constant must be True or False")

    def decompose(self):
        """
        Decompose values and units.

        Returns
        -------
        tuple with values and units.
        """
        return self.value, self.unit

    @staticmethod
    def decompose_expr(expr, quantity=True):
        """
        Extract value and unit from an sympy expression or an array with sympy expressions.

        Parameters
        ----------
        expr :numpy.ndarray, sympy.core.mul.Mul
            Sympy expression
        quantity : bool
            If True (default), the output is an Quantity object.

        Returns
        -------
        tuple with (values, units)
        """
        if quantity:
            value, unit = decompose_expr_to_atoms(expr)
            return Quantity(value, unit)
        else:
            return decompose_expr_to_atoms(expr)

    def set_name(self, name):
        """
        Set name of Quantity.

        Parameters
        ----------
        name : str
            Name of Quantity.

        Returns
        -------
        None
        """
        self.name = name

    def convert_to(self, unit, inplace=False):
        """
        Convert a quantity to another unit.

        Parameters
        ----------
        unit : sympy.physics.units.quantities.Quantity, str
            An object that represents the unit associated with the input value.
            Must be an `sympy.physics.units.quantities.Quantity` object or a string parsable by
            the :mod:`~respy.units` package.
        inplace : bool
            If True the values of the actual class will be overwritten.

        Returns
        -------
        respy.units.Quantity or None

        """
        unit = get_unit(unit)

        try:
            dimension = unit.dimension.name

            if dimension == self.dimension:
                scaled_value = self.value.astype(self._dtype) * util.Units[str(dimension)][str(self.unit)].scale_factor
                value = scaled_value / util.Units[str(dimension)][str(unit)].scale_factor

            else:
                value = np.zeros_like(self.value, dtype=self._dtype)

                if len(self.value) == 1:
                    arg = convert_to_unit(self.expr, unit)
                    value[0] = arg.base
                    value = value.flatten()

                else:
                    shape = self.value.shape
                    expr = self.expr.flatten()
                    value = convert_to_unit(expr, unit)

                    value = value.base
                    value = value.reshape(shape)

            dtype = value.dtype

        except AttributeError:
            value = np.zeros_like(self.value, dtype=self._dtype)

            if len(self.value) == 1:
                arg = convert_to_unit(self.expr, unit)
                value[0] = arg.base
                value = value.flatten()

            else:
                shape = self.value.shape
                expr = self.expr.flatten()
                value = convert_to_unit(expr, unit)

                value = value.base
                value = value.reshape(shape)

            dtype = value.dtype

        if inplace:
            self.__set_attributes(unit, value, self._dtype, self.copy, self.order, self.subok, False,
                                  self.ndmin)
        else:
            return self.__create_new_instance(value, unit, self.name)

    # --------------------------------------------------------------------------------------------------------
    # Private Methods
    # --------------------------------------------------------------------------------------------------------

    def __set_attributes(self, unit, value, dtype, copy, order, subok, constant, ndmin):
        if unit is None or isinstance(unit, type(One)):
            self.unit = None
        else:
            self.unit = get_unit(unit)

        self.value = value
        self._dtype = dtype
        self.copy = copy
        self.order = order
        self.subok = subok
        self.constant = constant
        self.ndmin = ndmin

        try:
            self.dimension = self.unit.dimension.name
        except AttributeError:
            self.dimension = None

    def __create_new_instance(self, value, unit=None, name=None, dtype=None):

        quantity_subclass = self.__class__

        if unit is None or unit is 1:
            unit = None
        elif isinstance(unit, type(One)):
            unit = None
        else:
            pass

        if dtype is None:
            dtype = self._dtype
        else:
            pass

        value = np.array(value, dtype=dtype, copy=False, order=self.order,
                         subok=self.subok)

        value = np.atleast_1d(value)
        view = value.view(quantity_subclass)

        view.__set_attributes(unit, value, dtype, self.copy, self.order, self.subok, self.constant, self.ndmin)
        view.set_name(name)

        return view

    def __check_other(self, other):
        if hasattr(other, 'quantity'):
            pass
        else:
            other = np.atleast_1d(np.asarray(other))

        return other
