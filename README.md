Eltrur
======

Eltrur is a web application that receives and records the screenshot from the
Rurtle runtime tests on Travis-CI.

Usage
-----

Visit the instance at https://kingdread.de/eltrur/

Installation
------------

If you really want to host your own instance, install the required python
modules (see `requirements.txt`) and hook up the WSGI application to your
webserver. The exact steps depend on your webserver.

**This program is very specific to Rurtle. It contains many hard-coded
references. If you want to host your own instance, please make sure to change
all references to Rurtle/my instance.**

Configuration
-------------

1) Edit the source
2) Create a `settings.py`:

```
UPLOAD_KEY = "your_secret_upload_key"
DATA_DIR = "data/"
```

Make sure to keep `UPLOAD_KEY` secret and set it as a secure travis environment
variable.

Make sure to edit `tests/upload_results.py` in your Rurtle source directory to
point it to the right instance.

License
-------

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
