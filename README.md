# Murmeli
An encrypted, serverless friend-to-friend messaging application using PGP encryption and Tor's hidden services.

The tool is very much still under development.  The code published here currently covers the startup wizard and some components of the Murmeli application itself.  This includes the step-by-step tool to check dependencies, set up the database, connect to tor and create the unique keypair for encryption; also the basic management of the contacts list and sending and receiving messages.  The rest of the code will follow as it becomes more stable, but feedback is welcome on the code published so far.

More information about Murmeli is published online here:
    https://activityworkshop.net/software/murmeli/
including explanations of the concepts and ideas, some screenshots and a pair of youtube videos demonstrating setup, establishing contact and exchanging messages.  Feedback, criticism and review of these proposals are very welcome.

Put briefly, the aim is to produce a way of sending encrypted messages from peer to peer, without using a server.  The communication is done by both sides publishing tor hidden services, and the encryption is done using asymmetric PGP once public keys have been exchanged and verified.  Because it runs without a server, peers have to be online at the same time in order to exchange messages.  However, mutual trusted peers can act as blind relays for the encrypted messages, thereby reducing latency.

It uses Python3 and Qt for the desktop application, and it stores the messages inside a local file-based database.  It should be cross-platform, but until now it has only been tested on linux (Debian, Raspbian and Mint) with all dependencies available from the standard (stable) repositories.  Testing on Windows is ongoing.

Please try out the code and report back any difficulties encountered.  The tool can be started with:

	python3 startmurmeli.py

and the tests can be run with (for example):

        cd test
        PYTHONPATH=.. python3 ssdbtest.py

All feedback and help is very welcome.

## Known issues

* In the startup wizard, it would be nice to be able to select the executable paths with a file dialog.
* The messages view doesn't yet have any sorting or paging options, it just shows all messages with the newest first.
* It's not yet clear whether each message has been 'read' or is 'unread'.
* Search results are not yet highlighted.
* The punch-card now has added punch (but github doesn't show punch-cards any more).

Given the problems which were caused by the use of Mongo as a database, it was necessary
to replace it with a different, simpler solution.  This may not provide all the power of Mongo's
functionality (in particular its search), but it avoids many of the authentication issues,
service starting/stopping issues, cross-platform incompatibilities and resource usage.

* There's an intermittent "Segmentation Fault" problem somewhere in the Qt library which is proving difficult to reproduce.
* Even though Murmeli doesn't use Mongo as a database any more, it still relies on pymongo for its bson processing.  It would be nice to remove this dependency.
* It appears that all the Qt4 code needs porting to use Qt5 (in particular the signals- and slots-handling) and also porting the use of QtWebKit to the new QtWebEngine.
