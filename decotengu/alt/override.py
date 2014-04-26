#
# DecoTengu - dive decompression library.
#
# Copyright (C) 2013-2014 by Artur Wroblewski <wrobell@pld-linux.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""
Context manager for overriding float data type with a decimal data type.

By default, float type is used for decompression calculations. This module
allows to change the default and experiment with fixed point arithmetics.

The implementation mixes in local context manager from `decimal` module. In
the future, it should be probably allowed to use custom decimal types
without `decimal` module dependency.
"""

from decimal import Decimal, localcontext

class DecimalContext(object):
    """
    Context manager for float type override with decimal type.

    :var const: The `decotengu.const` module.
    :var model: The `decotengu.model` module.
    :var tab: The `decotengu.alt.tab` module.
    :var const_data: Original values for `decotengu.const` values.
    :var model_data: Original values for `decotengu.model` values.
    :var tab_data: Original values for `decotengu.alt.tab` values.
    :var type: Overriding decimal type.
    :var prec: Precision of decimal type.
    :var ctx: Decimal type context (from decimal module).
    """
    def __init__(self, type=Decimal, prec=9):
        """
        Create context manager.

        :param type: Overriding decimal type.
        :param prec: Precision to use.
        """
        import decotengu.const as const
        import decotengu.model as model
        import decotengu.alt.tab as tab
        self.const = const
        self.model = model
        self.tab = tab

        # enforce precision on init with '+', see decimal module docs
        self.type = lambda v: +type(v)
        self.prec = prec
        self.ctx = localcontext()

        self.const_data = {}
        self.model_data = {}
        self.tab_data = {}


    def __enter__(self):
        """
        Override data type of constants of all known decompression models
        with decimal type.
        """
        ctx = self.ctx.__enter__()
        ctx.prec = self.prec

        attrs = ('WATER_VAPOUR_PRESSURE_DEFAULT', 'LOG_2')
        self._override(self.const, attrs, self.const_data)

        self.tab_data['exposure_t'] = self.tab.exposure_t
        exp_t = self.tab.exposure_t
        self.tab.exposure_t = lambda t, hl: \
            tuple(self.type(v) for v in exp_t(t, hl))

        for cls in (self.model.ZH_L16B_GF, self.model.ZH_L16C_GF):
            self.model_data[cls] = {}
            attrs = ('N2_A', 'N2_B', 'HE_A', 'HE_B', 'N2_HALF_LIFE', 'HE_HALF_LIFE')
            self._override(cls, attrs, self.model_data[cls], scalar=False)
            attrs = ('START_P_N2', 'START_P_HE')
            self._override(cls, attrs, self.model_data[cls])


    def __exit__(self, *args):
        """
        Param undo all changes to the constants of decompression models.
        """
        self._undo(self.const, self.const_data)
        self._undo(self.tab, self.tab_data)
        for cls in (self.model.ZH_L16B_GF, self.model.ZH_L16C_GF):
            self._undo(cls, self.model_data[cls])
        self.ctx.__exit__(*args)


    def _override(self, obj, attrs, data, scalar=True):
        """
        Override attributes data type of module or a class and save it in
        original data store.

        Supports scalar values and tuples and lists. No nested collections
        allowed at the moment.

        :param obj: Module or class.
        :param attrs: Attributes to override.
        :param data: Original data store (a dictionary (attribute -> value).
        :param scalar: A scalar if true, otherwise use treat as a collection.
        """
        for attr in attrs:
            value = getattr(obj, attr)
            data[attr] = value

            if scalar:
                value = self.type(value)
            else:
                value = type(value)(self.type(v) for v in value)
            setattr(obj, attr, value)


    def _undo(self, obj, data):
        """
        Undo overriden attributes of a module or class.

        :param obj: Module or class.
        :param data: Dictionary (attribute -> value) containing original
            values of module or class.
        """
        for attr in data:
            setattr(obj, attr, data[attr])


# vim: sw=4:et:ai