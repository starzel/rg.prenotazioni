# -*- coding: utf-8 -*-
from DateTime import DateTime
from pyinter.interval import Interval
from zope.component import Interface
from zope.interface.declarations import implements


class ISlot(Interface):

    '''
    Interface for a Slot object
    '''


class LowerEndpoint(int):

    ''' Lower Endpoint
    '''


class UpperEndpoint(int):

    ''' Upper Endpoint
    '''


class BaseSlot(Interval):

    ''' Overrides and simplifies pyinter.Interval
    '''
    implements(ISlot)
    _lower = Interval.CLOSED
    _upper = Interval.CLOSED
    context = None
    gate = ''

    @staticmethod
    def time2seconds(value):
        '''
        Takes a value and converts it into seconds

        :param value: a datetime or DateTime object
        '''
        if isinstance(value, int):
            return value
        if not value:
            return None
        if isinstance(value, DateTime):
            value = value.asdatetime()
        return (value.hour * 60 * 60 + value.minute * 60 + value.second)

    def __init__(self, start, stop, gate=''):
        '''
        Initialize an BaseSlot
        :param start:
        :param stop:
        :param gate:
        '''
        if start is not None:
            self._lower_value = LowerEndpoint(self.time2seconds(start))
        if stop is not None:
            self._upper_value = UpperEndpoint(self.time2seconds(stop))
        self.gate = gate

    def __len__(self):
        ''' The length of this object
        '''
        if not self:
            return 0
        return self._upper_value - self.lower_value

    def __nonzero__(self):
        ''' Check if this should be True
        '''
        if (isinstance(self._lower_value, int) and
                isinstance(self._upper_value, int)):
            return 1
        else:
            return 0

    def __sub__(self, value):
        ''' Subtract something from this
        '''
        if isinstance(value, Interval):
            value = [value]

        # We filter not overlapping intervals
        good_intervals = [x for x in value if x.overlaps(self)]
        points = []
        [points.extend([x.lower_value, x.upper_value])
         for x in good_intervals]
        points.sort()

        start = self.lower_value
        intervals = []
        for x in points:
            if isinstance(x, LowerEndpoint) and x > start:
                    intervals.append(BaseSlot(start, x))
                    # we raise the bar waiting for another stop
                    start = self.upper_value
            elif isinstance(x, UpperEndpoint):
                start = x
        intervals.append(BaseSlot(start, self.upper_value))
        return intervals

    def value_hr(self, value):
        ''' format value in a human readable fashion
        '''
        if not value:
            return ''
        hour = str(value // 3600).zfill(2)
        minute = str((value % 3600) / 60).zfill(2)
        return '%s:%s' % (hour, minute)

    def start(self):
        ''' Return the starting time
        '''
        return self.value_hr(self._lower_value)

    def stop(self):
        ''' Return the starting time
        '''
        return self.value_hr(self._upper_value)


class Slot(BaseSlot):
    implements(ISlot)

    def __init__(self, context):
        '''
        @param context: a Prenotazione object
        '''
        self.context = context
        BaseSlot.__init__(self,
                          context.getData_prenotazione(),
                          context.getData_scadenza(),
                          self.context.getGate())
