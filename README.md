# obstool
A Django-based observing tool for amateur astronomy

This is a scaled-down version of software I wrote for the Carnegie RR-Lyra
project (CARRS). The main idea is to give the user a list of objects in a
database that can be viewed at any given time. The code uses pyephem to precess
coordinates, compute altitude, azimuth, airmass, etc. Django is used to deliver
the HTML to a browser.

Ultimately, the code should be able to run on a web-server (apache) or
stand-alone on a computer if there is no internet.

## Requirements:
  * [Python 3.x](http://www.python.org)
  * [pyephem](http://rhodesmill.org/pyephem/)
  * [Python Imaging Library (PIL)](http://www.pythonware.com/products/pil/)
  * [django](https://www.djangoproject.com/)
  * [Paper.js](http://paperjs.org)
  * [astropy](http://www.astropy.org/)
  * [bokeh](https://docs.bokeh.org/en/latest/)

## Installation:

Easiest and safest way to install is using miniconda or anaconda:

    conda create -n obstool ephem django astropy bokey
    cd someplace
    git clone https://github.com/chrisrburns/obstool

## Running the tool:

Just use django's development server locally on your computer/laptop:

    cd someplace/obstool
    python manage.py runserver

Open a browser and navigate to http://localhost:8000/

If you want to deploy on a local area network or even over the web, a more
robust setup is required. See `DEPLOY.txt` for how to do this.

## Screenshot:

   ![Screenshot](https://github.com/chrisrburns/obstool/blob/1a7e41335586f63f5e39dcece4fdea7aabc67b17/screeshot.png)
