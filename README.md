# Murmeli
An encrypted, serverless friend-to-friend messaging service.

There isn't any source published for this tool because it is still under development.  But there is information published online here:
    http://activityworkshop.net/software/murmeli/
including explanations of the concepts and ideas, and some screenshots.  Feedback, criticism and review of these proposals are very welcome.

Put briefly, the aim is to produce a way of sending encrypted messages from peer to peer, without using a server.  The communication is done by both sides publishing tor hidden services, and the encryption is done using asymmetric PGP once public keys have been exchanged and verified.

It uses Python3 and Qt for the desktop application, and it stores the messages inside a local Mongodb database.  It should be cross-platform, but until now it has only been tested on linux (Debian, Raspbian and Mint) with all dependencies available from the standard repositories.

More details will follow once the functionality reaches a publishable state.
