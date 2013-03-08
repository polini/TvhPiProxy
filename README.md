TvhPiProxy
==========

Tvheadend proxy to get XBMC on Raspberry Pi to work with Tvheadend

## Usage

Download tvhpiproxy.py and run

	$ ./tvhpiproxy.py

Then point the Tvheadend add-on of your Raspberry Pi's XBMC to HTSP port 9983 instead of 9982

You can also pass specific ports or a hostname when you run TvhPiProxy on another host than Tvheadend

	$ ./tvhpiproxy.py [proxyport] [tvheadend-hostname] [tvheadend-htsp-port]

e.g.

	$ ./tvhpiproxy.py 9992 192.168.0.1 9982