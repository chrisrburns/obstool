# obstool
A Django-based observing tool for amateur astronomy

This is a scaled-down version of software I wrote for the Carnegie RR-Lyra
project (CARRS). The main idea is to give the user a list of objects in a
database that can be viewed at any given time. The code uses pyephem to precess
coordinates, compute altitude, azimuth, airmass, etc. Django is used to deliver
the HTML to a browser.

Ultimately, the code should be able to run on a web-server (apache) or
stand-alone on a computer if there is no internet.

Requirements:
  * [Python 2.7](http://www.python.org)
  * [pyephem >= 3.7.6.0](http://rhodesmill.org/pyephem/)
  * [Python Imaging Library (PIL) >= 1.1.7](http://www.pythonware.com/products/pil/)
  * [django 1.8.4](https://www.djangoproject.com/)
  * [Paper.js](http://paperjs.org)
  * [astropy 1.2.1](http://www.astropy.org/)

Screenshot:

   ![Screenshot](https://github.com/chrisrburns/obstool/blob/master/screeshot.png?raw=true)
