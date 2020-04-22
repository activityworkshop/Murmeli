'''Module for utils for serializing and deserializing contact lists'''

import json


def _make_set_from(contacts):
    '''Make a set of the unique tuples in the given list'''
    contacts_set = set()
    for found_contact in contacts:
        if found_contact and len(found_contact) == 2 and len(found_contact[0]) >= 16:
            contacts_set.add(tuple(found_contact))
    return contacts_set

def contacts_to_string(contacts):
    '''Produce a string to describe the given contact tuples'''
    contacts_set = _make_set_from(contacts)
    return json.dumps(list(contacts_set))

def contacts_from_string(contact_string):
    '''Parse the given string to give a list of contact tuples'''
    if contact_string:
        try:
            contacts_set = _make_set_from(json.loads(contact_string))
            return list(contacts_set)
        except json.decoder.JSONDecodeError:
            pass
    return []
