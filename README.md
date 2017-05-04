# Murmeli
An encrypted, serverless friend-to-friend messaging service.

The tool is very much still under development.  The code published here currently covers the startup wizard and some components of the Murmeli application itself.  This includes the step-by-step tool to check dependencies, set up the database, connect to tor and create the unique keypair for encryption; also the basic management of the contacts list and sending and receiving messages.  The rest of the code will follow as it becomes more stable, but feedback is welcome on the code published so far.

More information about Murmeli is published online here:
    http://activityworkshop.net/software/murmeli/
including explanations of the concepts and ideas, some screenshots and a youtube video.  Feedback, criticism and review of these proposals are very welcome.

Put briefly, the aim is to produce a way of sending encrypted messages from peer to peer, without using a server.  The communication is done by both sides publishing tor hidden services, and the encryption is done using asymmetric PGP once public keys have been exchanged and verified.  Because it runs without a server, peers have to be online at the same time in order to exchange messages.  However, mutual trusted peers can act as blind relays for the encrypted messages, thereby reducing latency.

It uses Python3 and Qt for the desktop application, and it stores the messages inside a local Mongodb database.  It should be cross-platform, but until now it has only been tested on linux (Debian, Raspbian and Mint) with all dependencies available from the standard (stable) repositories.  Testing on Windows is ongoing.

Please try out the code and report back any difficulties encountered.  The tool can be started with:

	python3 startmurmeli.py

and the tests can be run with (for example):

        cd test
        export PYTHONPATH=..
        python3 databasetest.py

All feedback and help is very welcome.

## Known issues

* The DbClient checks to see if the 'mongod' database server is running or not, to see whether
 it needs to be started.  On Linux it can do this by trying to create a 'MongoClient' object,
 and if the server isn't running, this will fail with a ConnectionFailure: Connection refused.
 On Windows, it seems that it behaves differently and the client
 object can be created even if the mongod server isn't even installed!  The result is that the
 DbClient thinks that mongod is already running, and doesn't try to start it.
 (Murmeli could try to query the Mongo server if it thinks it's running on Windows, but unfortunately
  if there's no server then querying fails with a Windows error, not a python exception.)
* Mongod requires a Windows hotfix to be installed if you're using Windows 7.
* Mongod appears to create several hundred megabytes of pre-allocated space under /var/lib/mongodb/journal which can raise issues on platforms with limited space (eg a pi).
* In the startup wizard, it would be nice to be able to select the executable paths with a file dialog.
* The punch-card now has added punch.

Given the problems which are being caused by the use of Mongo as a database, it will perhaps be necessary
to replace this with a different, simpler solution.  This may not provide all the power of Mongo's
functionality (in particular its search), but it would avoid may of the authentication issues,
service starting/stopping issues, cross-platform incompatibilities and resource usage.
