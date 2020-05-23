'''Post service, dealing with outgoing post'''

import threading
import time
import socks
from murmeli.system import System, Component
from murmeli.signals import Timer
from murmeli.message import StatusNotifyMessage, Message, RelayMessage
from murmeli import dbutils
from murmeli import imageutils
from murmeli import guinotification


class DefaultMessageTransport:
    '''Class which the outgoing postman usually uses to send messages.
       May be substituted by another object for use in unit tests.'''

    @staticmethod
    def send_message(msg_bytes, whoto):
        '''Try to send the given message over the default mechanism'''
        try:
            sock = socks.socksocket()
            sock.setproxy(socks.PROXY_TYPE_SOCKS4, "localhost", 11109)
            sock.connect((whoto + ".onion", 11009))
            num_sent = sock.send(msg_bytes)
            sock.close()
            if num_sent != len(msg_bytes):
                print("Num bytes sent:", num_sent, "but message has length:", len(msg_bytes))
            else:
                return PostService.RC_MESSAGE_SENT
        except Exception as exc:
            print("Socks send threw something:", exc)
        return PostService.RC_MESSAGE_FAILED


class PostService(Component):
    '''System component for managing the outgoing post'''

    # Return codes
    RC_MESSAGE_SENT = 1
    RC_MESSAGE_IGNORED = 2
    RC_MESSAGE_FAILED = 3
    RC_MESSAGE_INVALID = 4

    def __init__(self, parent, transport=None):
        Component.__init__(self, parent, System.COMPNAME_POSTSERVICE)
        self.work_lock = threading.Lock()
        self.flush_timer = None
        self.need_to_flush = True
        self.step_counter = -1
        self.running = False
        self.flush_interval = 30 # By default, flush every 30 seconds
        self.transport = transport or DefaultMessageTransport()
        self.should_broadcast = True

    def set_timer_interval(self, timer_secs):
        '''Set the interval to a non-default value (especially for tests)'''
        self.flush_interval = timer_secs
        self.step_counter = 0

    def checked_start(self):
        '''Start the separate threads'''
        self.running = True
        if self.flush_interval:
            self.flush_timer = Timer(self.flush_interval, self._flush)
        return True

    def stop(self):
        '''Stop this component'''
        self.running = False
        if self.flush_timer:
            self.flush_timer.stop()

    def request_broadcast(self):
        '''Request a broadcast in a separate thread'''
        self.step_counter = -1
        self.request_flush()

    def request_flush(self):
        '''Request a flush in a separate thread'''
        self.need_to_flush = True
        if self.flush_interval == 0:
            Timer(1, self._flush, repeated=False)

    def _flush(self):
        '''Flush the outbox'''
        self.step_counter = (self.step_counter + 1) % 10
        if not self.step_counter:
            self._broadcast()
        if not self.need_to_flush:
            return
        if self.work_lock.acquire(timeout=2):
            print("Flush")
            self.need_to_flush = False
            self.call_component(System.COMPNAME_GUI, "notify_gui",
                                notify_type=guinotification.NOTIFY_OUTBOX_FLUSHING)
            # Look in the outbox for messages
            database = self.get_component(System.COMPNAME_DATABASE)
            messages_found = 0
            messages_sent = 0
            failed_recpts = set()
            # Loop twice over all messages, firstly dealing with priority messages
            for flush_iter in range(2):
                print("Flush iter %d" % flush_iter)
                for msg in database.get_outbox():
                    if not msg:
                        continue    # message already deleted
                    if not self.running:
                        break    # flushing stopped from outside
                    if flush_iter == 0:
                        messages_found += 1
                        recipient = msg.get('recipient')
                        if not self.call_component(System.COMPNAME_CONTACTS,
                                                   "is_online", tor_id=recipient):
                            continue # not a priority for the first iter
                    msg_sent, should_delete = self.deal_with_outbox_msg(msg, failed_recpts)
                    if msg_sent:
                        messages_sent += 1
                        self.call_component(System.COMPNAME_GUI, "notify_gui",
                                            notify_type=guinotification.NOTIFY_MSG_SENT)
                    if should_delete \
                      and not database.delete_from_outbox(index=msg.get("_id")):
                        print("Failed to delete from outbox:", msg)

                    # Wait inbetween sending to avoid overloading the network
                    time.sleep(3)

            print("From %d messages, I managed to send %d" % (messages_found, messages_sent))
            # We tried to send a message to these recipients but failed - set them to be offline
            for recpt in failed_recpts:
                self.call_component(System.COMPNAME_CONTACTS, "gone_offline",
                                    tor_id=recpt)
            print("Finished flush, releasing lock")
            self.work_lock.release()

    def deal_with_outbox_msg(self, msg, failed_recpts):
        '''Deal with a message in the outbox, trying to send if possible'''
        # send_timestamp = msg.get('timestamp', None) # not used yet
        # TODO: if timestamp is too old, either delete the message or move to inbox
        # Some messages have a single recipient, others only have a recipientList
        recipient = msg.get('recipient')
        if recipient:
            return self.deal_with_single_recipient(msg, recipient, failed_recpts)
        if msg.get('recipientList'):
            return self.deal_with_relayed_message(msg, failed_recpts)

        print("msg in outbox had neither recipient nor recipientList?", msg)
        msg_sent = False
        should_delete = False
        return (msg_sent, should_delete)


    def deal_with_single_recipient(self, msg, recipient, failed_recpts):
        '''Try to send the given message to the specified recipient'''
        print("Dealing with single recipient:", recipient)
        msg_bytes = None
        msg_sent = False
        should_delete = False
        send_result = self.RC_MESSAGE_IGNORED
        database = self.get_component(System.COMPNAME_DATABASE)
        # Check recipient status, if it's deleted then delete message also
        if dbutils.get_status(database, recipient) in [None, 'deleted']:
            send_result = self.RC_MESSAGE_IGNORED
        elif recipient in failed_recpts:
            print("Not even bothering to try to send to '%s', previously failed" % recipient)
            send_result = self.RC_MESSAGE_FAILED
        else:
            msg_bytes = imageutils.string_to_bytes(msg['message'])
            send_result = self._send_message(msg_bytes, msg.get('encType'), recipient)
            msg_sent = (send_result == self.RC_MESSAGE_SENT)
            if msg_sent:
                # The recipient and I are both online
                self.call_component(System.COMPNAME_CONTACTS, "come_online", tor_id=recipient)
                own_tor_id = dbutils.get_own_tor_id(database)
                self.call_component(System.COMPNAME_CONTACTS, "come_online", tor_id=own_tor_id)
                self.call_component(System.COMPNAME_LOGGING, "log",
                                    logstr="Sent '%s' to '%s'" % (msg.get('msgType'), recipient))

        if send_result in [self.RC_MESSAGE_IGNORED, self.RC_MESSAGE_SENT, self.RC_MESSAGE_INVALID]:
            # either recipient was blocked or message was sent, either way delete it
            should_delete = True
        else:
            failed_recpts.add(recipient)
            if not msg.get('queue'):
                print("Failed to send a message but it shouldn't be queued, deleting it")
                should_delete = True
            elif msg.get('relays'):
                print("Failed to send but I can try to relay it")
                signed_blob = self._get_blob_to_relay(msg, database)
                # Loop over each relay in the list and try to send to each one
                failed_relays = set()
                for relay in msg.get('relays'):
                    if relay not in failed_recpts and \
                      self._send_message(signed_blob, Message.ENCTYPE_RELAY,
                                         relay) == self.RC_MESSAGE_SENT:
                        print("Sent message to relay '%s'" % relay)
                        self.call_component(System.COMPNAME_LOGGING, "log",
                                            logstr="Relayed '%s'" % msg.get('msgType'))
                    else:
                        # Send failed, so add this relay to the list of failed ones
                        failed_relays.add(relay)
                        failed_recpts.add(relay)
                # here we update the list even if it hasn't changed
                database.update_outbox_message(index=msg["_id"],
                                               props={"relays":list(failed_relays)})
        return (msg_sent, should_delete)

    def _get_blob_to_relay(self, msg, database):
        '''Get a signed blob so the message can be relayed'''
        if msg.get('relayMessage'):
            return bytes(msg.get('relayMessage'))
        print("No signed blob in message, need to create one")
        msg_bytes = imageutils.string_to_bytes(msg['message'])
        signed_blob = RelayMessage.wrap_outgoing_message(self._sign_message(msg_bytes))
        database.update_outbox_message(index=msg["_id"],
                                       props={"relayMessage":list(signed_blob)})
        return signed_blob

    def _sign_message(self, msg_bytes):
        '''Sign the given bytes with our own key id'''
        database = self.get_component(System.COMPNAME_DATABASE)
        own_key_id = dbutils.get_own_key_id(database)
        crypto = self.get_component(System.COMPNAME_CRYPTO)
        if not own_key_id or not crypto:
            print("Failed to sign message using own key '%s'" % own_key_id)
            return None
        return crypto.sign_data(msg_bytes, own_key_id)

    def deal_with_relayed_message(self, msg, failed_recpts):
        '''Try to send the given relay message to a recipient list'''
        msg_sent = False
        should_delete = False
        msg_bytes = imageutils.string_to_bytes(msg['message'])
        failed_recpts_for_message = set()
        database = self.get_component(System.COMPNAME_DATABASE)
        own_tor_id = dbutils.get_own_tor_id(database)
        for recpt in msg.get('recipientList'):
            if recpt in failed_recpts:
                failed_recpts_for_message.add(recpt)
            else:
                send_result = self._send_message(msg_bytes, msg.get('encType'), recpt)
                if send_result == self.RC_MESSAGE_SENT:
                    msg_sent = True
                    self.call_component(System.COMPNAME_CONTACTS, "come_online", tor_id=recpt)
                    self.call_component(System.COMPNAME_CONTACTS, "come_online", tor_id=own_tor_id)
                elif send_result == self.RC_MESSAGE_FAILED:
                    # Couldn't send to this relay recipient
                    failed_recpts_for_message.add(recpt)
                    failed_recpts.add(recpt)
        if failed_recpts_for_message:
            # update msg with the new recipientList
            relays = list(failed_recpts_for_message)
            database.update_outbox_message(index=msg["_id"],
                                           props={"recipientList":relays})
            print("Failed to send a relay to:", failed_recpts_for_message)
        else:
            print("Relayed everything, now deleting relay message")
            should_delete = True
        return (msg_sent, should_delete)


    def _send_message(self, msg_bytes, enctype, whoto):
        '''Send the given message to the specified recipient'''
        if not msg_bytes:
            return self.RC_MESSAGE_INVALID
        print("Send_message (%d bytes) to '%s'" % (len(msg_bytes), whoto))
        if not whoto or not isinstance(whoto, str) or len(whoto) < 16:
            print("whoto no good, returning invalid")
            return self.RC_MESSAGE_INVALID
        database = self.get_component(System.COMPNAME_DATABASE)
        profile = database.get_profile(torid=whoto)
        status = profile.get('status') if profile else None
        if enctype == Message.ENCTYPE_NONE:
            status = 'allowed'
        if not status or status in ['deleted', 'blocked']:
            # recipient not found or unsuitable status
            print("status no good, returning ignored")
            return self.RC_MESSAGE_IGNORED
        # Use configured transport object to send
        if self.transport:
            print("passing on to self.transport")
            return self.transport.send_message(msg_bytes, whoto)
        print("no transport available, so failed")
        return self.RC_MESSAGE_FAILED

    def _broadcast(self):
        '''Broadcast our online status by adding to the outbox'''
        database = self.get_component(System.COMPNAME_DATABASE)
        if not database or not self.should_broadcast:
            return
        if self.work_lock.acquire(timeout=2):
            print("Broadcast")
            profile_list = database.get_profiles_with_status(["trusted", "robot"])
            if profile_list:
                crypto = self.get_component(System.COMPNAME_CRYPTO)
                msg = StatusNotifyMessage()
                msg.recipients = [c['torid'] for c in profile_list]
                dbutils.add_message_to_outbox(msg, crypto, database)
            self.work_lock.release()
        self.need_to_flush = True
