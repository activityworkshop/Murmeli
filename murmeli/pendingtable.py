'''Specifics about how rows are stored in the pending table'''

# Field names for table row
FN_FROM_ID = "fromId"
FN_PAYLOAD = "originalPayload"


def create_row(msg):
    '''Create a row to insert into the table from the given message'''
    row = {}
    if msg and msg.original_payload and msg.get_field(msg.FIELD_SENDER_ID):
        row = {FN_FROM_ID:msg.get_field(msg.FIELD_SENDER_ID),
               FN_PAYLOAD:msg.original_payload}
    return row
