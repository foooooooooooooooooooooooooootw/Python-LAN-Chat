# Python-LAN-Chat
A simple python GUI chat program that broadcasts on LAN with UDP. 

It also listens on LAN on port 12345, so anything sent there will be recorded.

Just open the program on any computers you have and all of them will receive the messages/files/images. At the moment I am thinking of making a similar program on mobile phones so that messages and files can be sent cross-platform.

The program does connect to the internet to download 1 icon and 1 placeholder image for files hosted on this repository, after which on subsequent startups it checks if the files exist and if they do should not connect to the internet anymore. 

On windows files are saved to AppData/Local/PythonLANChat.


# FAQ
### Why?
After trying to send text or images to another computer on the same network many times, I realized it was a huge pain and we should not have to rely on messaging services like whatsapp or telegram just to send things around. What if internet connection wasn't available?

### Why not leverage TCP or use another programming language?
TCP would need a server or even having to know your other device's IP in the case of a client-server architecture. Even then, you would be sending messages to only one other device at a time. This way is much easier and requires 0 set-up. 
I am most familiar with python and thought it would be fun to make a program with a GUI in python.

### Are you using the python logo as your program's icon?
No, it's actually two ethernet cables (one blue and one yellow) intertwined, similar to the python logo.

### You're a madman.
I prefer the title "Inspired by fever dreams".


