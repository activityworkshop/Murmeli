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

	python3 -m unittest test/test_system.py

or using automatic test discovery:

	python3 -m unittest discover test

Linting can be done with any tool of course, for example:

	pylint3 murmeli
 
All feedback and help is very welcome.

## Known issues

* In the startup wizard, it would be nice to be able to select the executable paths with a file dialog.
* The messages view doesn't yet have any sorting or paging options, it just shows all messages with the newest first.
* It's not yet clear whether each message has been 'read' or is 'unread'.
* Search results are not yet highlighted.

Given the problems which were caused by the use of Mongo as a database, it was necessary
to replace it with a different, simpler solution.  This may not provide all the power of Mongo's
functionality (in particular its search), but it avoids many of the authentication issues,
service starting/stopping issues, cross-platform incompatibilities and resource usage.

* There's an intermittent "Segmentation Fault" problem somewhere in the Qt library which is proving difficult to reproduce.  Hopefully this is gone with the move to Qt5, we'll see.
* It was necessary to port all the Qt4 code to use Qt5 (in particular the signals- and slots-handling) and also to port the use of QtWebKit to the new QtWebEngine.

## Redesign

There are efforts underway to redesign the architecture to make things more modular.  In particular, we'll plug together components at runtime instead of coupling them in a fixed way.  This should get rid of the singletons and make things much more testable.  It would also be desirable to plug together a partial system for tests, and for the robot instances a gui-less system without dependencies on Qt.  A regular raspberry pi (or similar) will then be able to run a gui-less robot, and a Scrollbot (or similar) will be able to use LEDs to show the robot's activity.

We'll also focus much more closely on the outputs of pylint and try to name things and indent things in a more pylint-friendly way.

Unfortunately this means that during the reorganisation the main Murmeli gui won't work for a while, as the focus will be on the components and their tests.

Another issue is the recent increase in the lengths of hidden service identifiers (and hence Murmeli ids), from 16 to 56 characters.  So there will be some changes necessary to remove the assumptions about id length.
