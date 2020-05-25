'''Module for the database classes based on SuperSimpleDb'''

import json
import os.path
import threading
from murmeli.system import System, Component
from murmeli import inbox


class SuperSimpleDb:
    '''Holds a super-simple database as a dictionary in memory
       and allows read/write from a persistent file.
       The dictionary holds tables, stored by name, where each
       table is a list of dictionaries.
       Rows of the table (items in the list) can be added, modified
       or deleted, although deleting a row just sets the row to an
       empty dictionary rather than removing it from the list.
       The key of each row is then just the index of the item in the list.
       When loaded from file, the empty rows are then ignored.'''

    def __init__(self, file_path=None):
        '''Constructor.  If filePath is None, then there will be no file loading or saving.'''
        self.db = {}    # Database, holding a dictionary of lists
        self.file_path = file_path
        if file_path:
            self.load_from_file()

    def load_from_file(self):
        '''Load the database using the path given in the constructor'''
        if self.file_path and os.path.exists(self.file_path):
            with open(self.file_path, "r") as fstream:
                try:
                    self.db = json.load(fstream)
                except json.decoder.JSONDecodeError:
                    print("Failed to load database - JSON error")

    def save_to_file(self):
        '''Save the database back to the specified file'''
        if self.file_path:
            # Save the copy to file (overwriting what was there)
            with open(self.file_path, "w") as fstream:
                json.dump(self.db, fstream)

    def get_table(self, table_name):
        '''Get the table with the given name, and create it if necessary'''
        table = self.db.get(table_name)
        if table:
            return table
        # Table doesn't exist yet, so create it
        self.db[table_name] = []
        return self.db[table_name]

    def compress_table(self, table_name):
        '''Compress the specified table by removing the empty rows'''
        if self.db.get(table_name):
            self.db[table_name] = [m for m in self.get_table(table_name) if m]

    def delete_from_table(self, table_name, index):
        '''Returns True if specified row could be deleted, otherwise False'''
        table = self.db.get(table_name)
        index = int(index) if isinstance(index, str) else index
        if table and len(table) > index:
            table[index] = {}
            return True
        return False

    def get_num_tables(self):
        '''Only needed for testing'''
        return len(self.db)

    @staticmethod
    def find_in_table(table, criteria):
        '''Look in the given table (obtained from eg get_table) for rows
           matching the given criteria.  Criteria may include lists.'''
        results = []
        for item in table:
            row_matches = True
            # Loop through criteria, checking that all of them match this row
            for crit_key in criteria.keys():
                crit_val = criteria.get(crit_key)
                row_val = item.get(crit_key)
                if crit_val is None or crit_val == "":
                    if row_val:
                        row_matches = False
                elif isinstance(crit_val, (int, str)):
                    if row_val != crit_val:
                        row_matches = False
                elif isinstance(crit_val, list):
                    if not row_val in crit_val:
                        row_matches = False
            if row_matches:
                results.append(item)

        return results


class Profile(dict):
    '''Wrapper class for profiles from the database'''
    def __init__(self, inDict):
        dict.__init__(self, inDict.copy())

    def __getitem__(self, key):
        val = dict.get(self, key)
        if not val and key == 'displayName':
            val = dict.get(self, 'name')
        if not val and key in ['displayName', 'name']:
            val = dict.get(self, 'torid')
        return val


class MurmeliDb(Component):
    '''Specialization of the SuperSimpleDb to handle Murmeli specifics'''
    db_write_lock = threading.Lock()

    TABLE_PROFILES = "profiles"
    TABLE_PENDING = "pendingcontacts"
    TABLE_OUTBOX = "outbox"
    TABLE_INBOX = "inbox"

    def __init__(self, parent, file_path=None):
        '''Constructor.  If file_path is None, then there will be no file loading or saving.'''
        Component.__init__(self, parent, System.COMPNAME_DATABASE)
        self.db = SuperSimpleDb(file_path)
        with threading.Condition(self.db_write_lock):
            self.compress_table(MurmeliDb.TABLE_INBOX)
            self.compress_table(MurmeliDb.TABLE_OUTBOX)
            # TODO: Remove expired outbox messages?

    def compress_table(self, table_name):
        '''Compress the table and renumber the indexes'''
        self.db.compress_table(table_name)
        # assume our caller already has a write lock
        for i, row in enumerate(self.db.get_table(table_name)):
            if row and row.get("_id") != i:
                row['_id'] = i

    def get_inbox(self):
        '''Get a copy of the inbox'''
        return [m.copy() for m in self.db.get_table(MurmeliDb.TABLE_INBOX) if m]

    def get_profiles(self):
        '''Get all the (non-blank) profiles'''
        tab = self.db.get_table(MurmeliDb.TABLE_PROFILES)
        return [Profile(i) for i in tab if i]

    def get_profiles_with_status(self, status):
        '''Get all the profiles with the given status'''
        tab = self.db.get_table(MurmeliDb.TABLE_PROFILES)
        if isinstance(status, list):
            return [Profile(i) for i in tab if i and i.get("status") in status]
        if status:
            return [Profile(i) for i in tab if i and i.get("status") == status]
        # status is empty, so return empty list
        return []

    def get_profile(self, torid=None):
        '''Get the profile for the given torid'''
        if torid:
            for prof in self.db.get_table(MurmeliDb.TABLE_PROFILES):
                if prof and prof.get("torid") == torid:
                    return Profile(prof)
        else:
            # No id given, so get our own profile
            for prof in self.db.get_table(MurmeliDb.TABLE_PROFILES):
                if prof and prof.get("status") == "self":
                    return Profile(prof)
            print("%d rows in profiles table, but self not found?"
                  % len(self.db.get_table(MurmeliDb.TABLE_PROFILES)))
        return None # not found

    def get_outbox(self):
        '''Get copies of all the messages in the outbox'''
        return [m.copy() for m in self.db.get_table(MurmeliDb.TABLE_OUTBOX) if m]

    @staticmethod
    def add_row_to_pending_table(row):
        '''Add the given row to the pending contacts table,
           if it isn't there in the table already'''
        if row:
            print("Add row to pending table:", row)

    def get_num_tables(self):
        '''Only needed for testing'''
        return self.db.get_num_tables()

    def add_row_to_inbox(self, msg):
        '''Append the given row to the inbox table'''
        with threading.Condition(self.db_write_lock):
            # Get current number in inbox, use this as index for msg
            inbox_table = self.db.get_table(MurmeliDb.TABLE_INBOX)
            msg['_id'] = len(inbox_table)
            inbox_table.append(msg)

    def delete_from_inbox(self, index):
        '''Delete the message at the given index from the inbox, return True on success'''
        return self.update_inbox_message(index, {inbox.FN_DELETED:True})

    def update_inbox_message(self, index, props):
        '''Update the inbox message at the given index'''
        if index is None or index < 0:
            return False
        with threading.Condition(self.db_write_lock):
            inbox_table = self.db.get_table(MurmeliDb.TABLE_INBOX)
            if len(inbox_table) > index:
                row = inbox_table[index]
                if row:
                    row.update(props)
                    return True
        return False

    def add_row_to_outbox(self, msg):
        '''Append the given row to the outbox'''
        assert isinstance(msg, dict)
        with threading.Condition(self.db_write_lock):
            # Get current number in outbox, use this as index for msg
            outbox = self.db.get_table(MurmeliDb.TABLE_OUTBOX)
            msg['_id'] = len(outbox)
            # print("Adding message to outbox:", repr(msg))
            outbox.append(msg)
        # Inform postman that a flush can be made now
        self.call_component(System.COMPNAME_POSTSERVICE, "request_flush")

    def delete_from_outbox(self, index):
        '''Delete the message at the given index from the outbox, return True on success'''
        with threading.Condition(self.db_write_lock):
            return self.db.delete_from_table(MurmeliDb.TABLE_OUTBOX, index)

    def delete_all_from_outbox(self):
        '''Delete all the messages from the outbox'''
        num_rows = len(self.db.get_table(MurmeliDb.TABLE_OUTBOX))
        for index in range(num_rows):
            self.delete_from_outbox(index)

    def update_outbox_message(self, index, props):
        '''Update the outbox message at the given index'''
        with threading.Condition(self.db_write_lock):
            outbox = self.db.get_table(MurmeliDb.TABLE_OUTBOX)
            if len(outbox) > index:
                row = outbox[index]
                if row:
                    row.update(props)
                    return True
        return False # failed

    def add_or_update_profile(self, profile):
        '''Either insert a new profile or update an existing one according to the id'''
        with threading.Condition(self.db_write_lock):
            tab = self.db.get_table(MurmeliDb.TABLE_PROFILES)
            new_id = profile.get("torid") if profile else None
            if not new_id:
                return False
            for found_profile in tab:
                if found_profile.get("torid") == new_id:
                    found_profile.update(profile)
                    return True
            tab.append(profile)
        return True

    def load_from_file(self):
        '''Load the database from file'''
        with threading.Condition(self.db_write_lock):
            self.db.load_from_file()

    def save_to_file(self):
        '''Save the database to file'''
        with threading.Condition(self.db_write_lock):
            self.db.save_to_file()

    def stop(self):
        '''Stop the database'''
        self.save_to_file()
        Component.stop(self)

    def find_in_table(self, table, criteria):
        '''Look in the given table (obtained from eg get_inbox) for rows
           matching the given criteria.  Criteria may include lists.'''
        return self.db.find_in_table(table, criteria)
