'''Specifics about how rows are stored in the inbox'''


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


def create_row(msg, context):
    '''Create a row to insert into the inbox from the given message and context'''
    row = {}
    print("Generate inbox row for msg:", msg, ", context:", context)
    return row
