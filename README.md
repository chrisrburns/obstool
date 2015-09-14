# obstool
A Django-based observing tool for amateur astronomy

This is a scaled-down version of software I wrote for the Carnegie RR-Lyra project (CARRS). The main idea is to give the user a list of objects in a database that can be viewed at any given time. The code uses pyephem to precess coordinates, compute altitude, azimuth, airmass, etc. Django is used to deliver the HTML to a browswer.

Ultimately, the code should be able to run on a web-server (apache) or stand-alone on a computer if there is no internet.
