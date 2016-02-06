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

## Known issues

* The DbClient checks to see if the 'mongod' database server is running or not, to see whether
 it needs to be started.  On Linux it can do this by trying to create a 'MongoClient' object,
 and if the server isn't running, this will fail with a ConnectionFailure: Connection refused.
 From some preliminary tests on Windows, it seems that it behaves differently and the client
 object can be created even if the mongod server isn't even installed!  The result is that the
 DbClient thinks that mongod is already running, and doesn't try to start it.
* Mongod requires a Windows hotfix to be installed if you're using Windows 7.
* Murmeli doesn't yet use any kind of authentication for the access to the Mongod server.  It's
 restricted to connections from the same machine, but other users on the same machine can connect
 to the server and read all the contents of the database.  This needs to be fixed at some point.
* The startup wizard assumes that the 'gpg' executable is in the path already, but this probably
 needs to be added to the panel in the same way that the tor and mongod paths are specified.
 It would be nice to be able to select the paths with a file dialog too.
