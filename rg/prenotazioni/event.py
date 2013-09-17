# -*- coding: utf-8 -*-

from Products.CMFCore.utils import getToolByName
from Products.DCWorkflow.DCWorkflow import WorkflowException
from rg.prenotazioni.adapters.booker import IBooker


def booking_created(context, event):
    try:
        factory_tool = getToolByName(context, 'portal_factory')
        if not factory_tool.isTemporary(context) and not context._at_creation_flag:
            wtool = getToolByName(context, 'portal_workflow')
            wtool.doActionFor(context, 'submit')
    except WorkflowException:
        pass


def reallocate_gate(obj):
    '''
    We have to reallocate the gate for this object
    '''
    container = obj.object.getPrenotazioniFolder()
    booking_date = obj.object.getData_prenotazione()
    new_gate = IBooker(container).get_available_gate(booking_date)
    obj.object.setGate(new_gate)


def reallocate_container(obj):
    '''
    If we moved Prenotazione to a new week we should move it
    '''
    import pdb;pdb.set_trace()
    container = obj.object.getPrenotazioniFolder()
    IBooker(container).fix_container(obj.object)
