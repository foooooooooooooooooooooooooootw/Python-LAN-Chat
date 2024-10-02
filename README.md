<p align="center">
  <img width="200" height="200" src="https://raw.githubusercontent.com/foooooooooooooooooooooooooootw/Python-LAN-Chat/main/pythonlanchat.ico?raw=true">
</p>

# Python LAN Chat
A party on your LAN and everyone's invited!

This is a simple python GUI chat program that broadcasts on LAN with UDP. 

It also listens on LAN on certain ports (default 12345), so anything sent there will be recorded.

Just open the program on any computers you have and all of them will receive the messages/files/images. At the moment I am thinking of making a similar program on mobile phones so that messages and files can be sent cross-platform.

The program does connect to the internet to download 1 icon and 1 placeholder image for files hosted on this repository (as well as dependencies if you don't have them and are running the python script instead of the binary) after which on subsequent startups it checks if the files exist and if they do should not connect to the internet anymore. 

On windows resource files are saved to AppData/Local/PythonLANChat.

This was tested on my home network with wired connections & no packet loss, so depending on your network configuration (i.e. routers, extenders, subnets, firewalls, internet interfaces, walls between device and access point) your mileage may vary. On my home network with computers connected to the same router with ethernet cables, I managed to send a 5+ GB file successfully. **Best use case is to send smaller files to many computers at once, and all the connections are wired to the same router**.

Point to note: this presumes your network is secure and no one is listening in on you. There is no encryption (may change in the future). Keep this in mind if for some reason you decide to send things over a public network - try not to send sensitive information like private keys.

The .pyw file will typically be the most updated since I don't compile a binary for every new version.


<p align="center">
  <img src="https://raw.githubusercontent.com/foooooooooooooooooooooooooootw/Python-LAN-Chat/main/staticdemo.jpg">
</p>

# FAQ
### Why?
After trying to send text or images to another computer on the same network many times, I realized it was a huge pain and we should not have to rely on messaging services like whatsapp or telegram just to send things around, or even go digging around for a thumbdrive.
Top reasons:
<ul>
  <li> What if internet wasn't available?</li>
  <li> What if you wanted to send it to multiple computers?</li>
  <li> What if it was a big file and there was a file limit like most online services have?</li>
  <li> Thumbdrives are also a great alternative except it gets real tiring to look for one, plug it in and out of computers etc. especially if you want to distribute a file to many computers</li>
</ul>

### Why not leverage TCP or use another programming language?
TCP would need a server or even having to know your other device's IP in the case of a client-server architecture. Even then, you would be sending messages to only one other device at a time. This way is much easier and requires 0 set-up. 
I am most familiar with python and thought it would be fun to make a program with a GUI in python.

### Are you using the python logo as your program's icon?
No, it's actually two ethernet cables (one blue and one yellow) intertwined, similar to the python logo.

### You're a madman.
I prefer the title "Inspired by fever dreams".


