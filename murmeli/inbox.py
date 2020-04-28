'''Specifics about how rows are stored in the inbox'''

from murmeli.message import (ContactRequestMessage, ContactAcceptMessage, ContactDenyMessage,
                             RegularMessage)

# Message contexts
MC_CONREQ_INCOMING = 2
MC_CONRESP_REFUSAL = 3
MC_CONRESP_ACCEPT = 4
MC_CONRESP_ALREADY_ACCEPTED = 5
MC_REFER_INCOMING = 6
MC_REFERREQ_INCOMING = 7
MC_NORMAL_INCOMING = 8

MC_NORMAL_SENT = 20

# Field names for table row
FN_MSG_INDEX = "_id"
FN_MSG_TYPE = "messageType"
FN_FROM_ID = "fromId"
FN_MSG_BODY = "messageBody"
FN_BEEN_READ = "messageRead"
FN_REPLIED = "messageReplied"
FN_DELETED = "deleted"
FN_TIMESTAMP = "timestamp"
FN_RECIPIENTS = "recipients"
FN_MSG_HASH = "messageHash"
# optional ones depending on type
FN_FROM_NAME = "fromName"
FN_ACCEPTED = "accepted"
FN_PUBLIC_KEY = "publicKey"
FN_FRIEND_ID = "friendId"
FN_FRIEND_NAME = "friendName"
FN_PARENT_HASH = "parentHash"
# for display only
FN_RECIPIENT_NAMES = "recipientNames"
FN_REPLY_ALL = 'replyAll'
FN_SENT_TIME_STR = "sentTimeStr"


def _create_base_row(msg_type, from_id, msg_body, timestamp, recipients, already_read=False,
                     already_replied=False):
    '''Create the row with the given fields'''
    return {FN_MSG_TYPE:msg_type, FN_FROM_ID:from_id, FN_MSG_BODY:msg_body, FN_TIMESTAMP:timestamp,
            FN_RECIPIENTS:recipients, FN_BEEN_READ:already_read, FN_REPLIED:already_replied}


def create_row(msg, context):
    '''Create a row to insert into the inbox from the given message and context'''
    row = {}
    if msg and context:
        # Ensure we have a valid timestamp string
        timestamp = msg.timestamp if msg.timestamp else msg.make_current_timestamp()
        if isinstance(timestamp, float):
            timestamp = msg.timestamp_to_string(timestamp)
        if context == MC_CONREQ_INCOMING and isinstance(msg, ContactRequestMessage):
            # Incoming contact request
            row = _create_base_row(msg_type="contactrequest",
                                   from_id=msg.get_field(msg.FIELD_SENDER_ID),
                                   msg_body=msg.get_field(msg.FIELD_MESSAGE),
                                   timestamp=timestamp, recipients=None)
            row[FN_FROM_NAME] = msg.get_field(msg.FIELD_SENDER_NAME)
            row[FN_PUBLIC_KEY] = msg.get_field(msg.FIELD_SENDER_KEY)

        elif context in [MC_CONRESP_REFUSAL, MC_CONRESP_ACCEPT, MC_CONRESP_ALREADY_ACCEPTED] \
          and isinstance(msg, (ContactAcceptMessage, ContactDenyMessage)):
            # Incoming contact response
            accepted = context in [MC_CONRESP_ACCEPT, MC_CONRESP_ALREADY_ACCEPTED]
            replied = context == MC_CONRESP_ALREADY_ACCEPTED
            msg_body = msg.get_field(msg.FIELD_MESSAGE) if accepted else ""
            row = _create_base_row(msg_type="contactresponse",
                                   from_id=msg.get_field(msg.FIELD_SENDER_ID),
                                   msg_body=msg_body, timestamp=timestamp,
                                   recipients=None, already_replied=replied)
            name_field = msg.FIELD_SENDER_NAME if accepted else msg.FIELD_SENDER_ID
            row[FN_FROM_NAME] = msg.get_field(name_field)
            row[FN_ACCEPTED] = accepted

        elif context in [MC_NORMAL_INCOMING, MC_NORMAL_SENT] and isinstance(msg, RegularMessage):
            # Incoming regular message or a copy of one which we sent
            from_id = msg.get_field(msg.FIELD_SENDER_ID)
            already_read = True if context == MC_NORMAL_SENT else False
            row = _create_base_row(msg_type="normal",
                                   from_id=from_id,
                                   msg_body=msg.get_field(msg.FIELD_MSGBODY),
                                   timestamp=timestamp,
                                   recipients=msg.get_field(msg.FIELD_RECIPIENTS),
                                   already_read=already_read)
            row[FN_PARENT_HASH] = msg.get_field(msg.FIELD_REPLYHASH)
    return row
