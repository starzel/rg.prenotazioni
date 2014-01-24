# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName
from datetime import date, timedelta
from plone.memoize.instance import memoize
from rg.prenotazioni.adapters.slot import BaseSlot
from zope.component import Interface
from zope.interface.declarations import implements


class IConflictManager(Interface):
    '''
    Interface for a booker
    '''


class ConflictManager(object):
    implements(IConflictManager)
    portal_type = 'Prenotazione'
    # We consider only those state as active. I.e.: prenotazioni rejected are
    # not counted!
    active_review_state = ['published', 'pending']

    def __init__(self, context):
        '''
        @param context: a PrenotazioniFolder object
        '''
        self.context = context

    @property
    @memoize
    def today(self):
        ''' Cache for today date
        '''
        return date.today()

    @property
    @memoize
    def first_valid_day(self):
        ''' The first day when you can book stuff

        ;return; a datetime.date object
        '''
        return self.context.getDaData().asdatetime().date()

    @property
    @memoize
    def last_valid_day(self):
        ''' The last day (if set) when you can book stuff

        ;return; a datetime.date object or None
        '''
        adata = self.context.getAData()
        if not adata:
            return
        return adata.asdatetime().date()

    @memoize
    def is_vacation_day(self, date):
        '''
        Check if today is a vacation day
        '''
        date_it = date.strftime('%d/%m/%Y')
        festivi = self.context.getFestivi()
        return date_it in festivi

    @memoize
    def is_configured_day(self, day):
        """ Returns True if the day has been configured
        """
        weekday = day.weekday()
        week_table = self.context.getSettimana_tipo()
        day_table = week_table[weekday]
        return any((day_table['inizio_m'],
                    day_table['end_m'],
                    day_table['inizio_p'],
                    day_table['end_p'],))

    @memoize
    def is_valid_day(self, day):
        """ Returns True if the day is valid
        """
        if day <= self.today:
            return False
        if self.is_vacation_day(day):
            return False
        if day < self.first_valid_day:
            return False
        if self.last_valid_day and day > self.last_valid_day:
            return False
        return self.is_configured_day(day)

    @property
    @memoize
    def prenotazioni(self):
        ''' The prenotazioni context state view
        '''
        return self.context.restrictedTraverse('@@prenotazioni_context_state')

    @property
    @memoize
    def base_query(self):
        '''
        A query that returns objects in this context
        '''
        return {'portal_type': self.portal_type,
                'path': '/'.join(self.context.getPhysicalPath())}

    def get_limit(self):
        '''
        Get's the limit for concurrent objects
        It is given by the number of active gates (if specified)
        or defaults to one
        There is also a field that disables gates, we should remove them from
        this calculation
        '''
        if not self.prenotazioni.get_gates():
            return 1
        return len(self.prenotazioni.get_available_gates())

    def unrestricted_prenotazioni(self, **kw):
        '''
        Query our prenotazioni
        '''
        query = self.base_query.copy()
        query.update(kw)
        pc = getToolByName(self.context, 'portal_catalog')
        brains = pc.unrestrictedSearchResults(**query)
        return brains

    def search_bookings_by_date_range(self, start, stop, **kw):
        '''
        Query our prenotazioni
        '''
        query = kw.copy()
        query['Date'] = {'query': [start, stop],
                         'range': 'min:max'}
        return self.unrestricted_prenotazioni(**query)

    def get_choosen_slot(self, data):
        ''' Get's the slot requested by the user
        '''
        tipology = data.get('tipology', '')
        tipology_duration = self.prenotazioni.get_tipology_duration(tipology)
        start = data.get('booking_date', '')
        end = start + timedelta(seconds=tipology_duration * 60)
        slot = BaseSlot(start, end)
        return slot

    def extend_availability(self, slots, gate_slots):
        ''' We add slots to the gate_slots list and we make unions
        when they overlap.
        '''
        for i in range(len(gate_slots)):
            for slot in slots:
                if gate_slots[i].overlaps(slot):
                    interval = gate_slots[i].union(slot)
                    gate_slots[i] = BaseSlot(interval.lower_value,
                                             interval.upper_value)

        return gate_slots + slots

    def add_exclude(self, exclude, availability):
        ''' Extends the availability list adding the slot we are moving
        '''
        for key in exclude.iterkeys():
            if availability.get(key, None):
                availability[key] = self.extend_availability(exclude[key],
                                                             availability[key])

        return availability

    def conflicts(self, data, exclude=None):
        '''
        Check if we already have a conflictual booking

        :param exclude: exclude a time slot (useful when we want to move
                        something).
                        Exclude should be a dict in the form
                        {'gate1' : [slot11, slot12, ...],
                         'gate2' : [slot21, slot22, ...],
                        }
        '''
        booking_date = data.get('booking_date', '')
        slot = self.get_choosen_slot(data)
        availability = (self.prenotazioni
                        .get_free_slots(booking_date))

        if exclude:
            availability = self.add_exclude(exclude, availability)

        for gate_slots in availability.itervalues():
            for gate_slot in gate_slots:
                if slot in gate_slot:
                    return False
        return True
