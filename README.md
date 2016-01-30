# Murmeli
An encrypted, serverless friend-to-friend messaging service.

The tool is very much still under development.  The code published here currently just covers the startup wizard, not (yet) the Murmeli application itself but just the step-by-step tool to check dependencies, set up the database, connect to tor and create the unique keypair for encryption.  The rest of the code will follow as it becomes more stable, but feedback is welcome on the wizard code.

More information about Murmeli is published online here:
    http://activityworkshop.net/software/murmeli/
including explanations of the concepts and ideas, and some screenshots.  Feedback, criticism and review of these proposals are very welcome.

Put briefly, the aim is to produce a way of sending encrypted messages from peer to peer, without using a server.  The communication is done by both sides publishing tor hidden services, and the encryption is done using asymmetric PGP once public keys have been exchanged and verified.  Because it runs without a server, peers have to be online at the same time in order to exchange messages.  However, mutual trusted peers can act as blind relays for the encrypted messages, thereby reducing latency.

It uses Python3 and Qt for the desktop application, and it stores the messages inside a local Mongodb database.  It should be cross-platform, but until now it has only been tested on linux (Debian, Raspbian and Mint) with all dependencies available from the standard repositories.

Please try out the code and report back any difficulties encountered.  The tool can be started with:

	python3 startmurmeli.py

All feedback and help is very welcome.

