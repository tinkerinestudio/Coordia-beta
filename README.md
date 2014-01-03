Coordia beta v0.2.2 by Tinkerine Studio
Coordia is based on Pronterface and runs skeinforge in the background for slice commands (with pypy for quicker slicing).

For questions, comments or feedback, feel free to email: support@tinkerines.com 



Printrun consists of printcore, pronsole and pronterface, and a small collection of helpful scripts.

  * printcore.py is a library that makes writing reprap hosts easy
  * pronsole.py is an interactive command-line host software with tabcompletion goodness
  * pronterface.py is a graphical host software with the same functionality as pronsole
  * webinterface.py is a browser-usable remote control function for Pronterface


## Windows

A precompiled version is available at http://www.tinkerines.com/forum/?page_id=5/coordia/coordia-ditto-control-host-beta

## Mac OS X

A precompiled version is available at http://www.tinkerines.com/forum/?page_id=5/coordia/coordia-ditto-control-host-beta


# Running from Source

Running Coordia from source requires:
-A version of skeinforge (put the folders "skeinforge_application" and "fabmetheus_utilities" in the root of Coordia)
-Everything pronterface needs.

The following has been copied from the pronterface readme:


## Dependencies

To use pronterface, you need:

  * python (ideally 2.6.x or 2.7.x),
  * pyserial (or python-serial on ubuntu/debian),
  * pyglet
  * pyreadline (not needed on Linux) and
  * wxPython

Please see specific instructions for Windows and Mac OS X below. Under Linux, you should use your package manager directly (see the "GETTING PRINTRUN" section)

## Windows

Download the following, and install in this order:

  1. http://python.org/ftp/python/2.7.2/python-2.7.2.msi
  2. http://pypi.python.org/packages/any/p/pyserial/pyserial-2.5.win32.exe
  3. http://downloads.sourceforge.net/wxpython/wxPython2.8-win32-unicode-2.8.12.0-py27.exe
  4. http://launchpad.net/pyreadline/1.7/1.7/+download/pyreadline-1.7.win32.exe
  5. http://pyglet.googlecode.com/files/pyglet-1.1.4.zip

For the last one, you will need to unpack it, open a command terminal, 
go into the the directory you unpacked it in and run
`python setup.py install`

## Mac OS X Lion

  1. Ensure that the active Python is the system version. (`brew uninstall python` or other appropriate incantations)
  2. Download an install [wxPython2.8-osx-unicode] matching to your python version (most likely 2.7 on Lion, 
        check with: python --version) from: http://wxpython.org/download.php#stable
  Known to work PythonWX: http://superb-sea2.dl.sourceforge.net/project/wxpython/wxPython/2.8.12.1/wxPython2.8-osx-unicode-2.8.12.1-universal-py2.7.dmg
  3. Download and unpack pyserial from http://pypi.python.org/packages/source/p/pyserial/pyserial-2.5.tar.gz
  4. In a terminal, change to the folder you unzipped to, then type in: `sudo python setup.py install`
  5. Repeat 4. with http://http://pyglet.googlecode.com/files/pyglet-1.1.4.zip

The tools will probably run just fine in 64bit on Lion, you don't need to mess
with any of the 32bit settings. In case they don't, try 
  5. export VERSIONER_PYTHON_PREFER_32_BIT=yes
in a terminal before running Pronterface

## Mac OS X (pre Lion)

A precompiled version is available at http://koti.kapsi.fi/~kliment/printrun/

  1. Download and install http://downloads.sourceforge.net/wxpython/wxPython2.8-osx-unicode-2.8.12.0-universal-py2.6.dmg
  2. Grab the source for pyserial from http://pypi.python.org/packages/source/p/pyserial/pyserial-2.5.tar.gz
  3. Unzip pyserial to a folder. Then, in a terminal, change to the folder you unzipped to, then type in:
     
     `defaults write com.apple.versioner.python Prefer-32-Bit -bool yes`
     
     `sudo python setup.py install`

Alternatively, you can run python in 32 bit mode by setting the following environment variable before running the setup.py command:

This alternative approach is confirmed to work on Mac OS X 10.6.8. 

`export VERSIONER_PYTHON_PREFER_32_BIT=yes`

`sudo python setup.py install`

Then repeat the same with http://http://pyglet.googlecode.com/files/pyglet-1.1.4.zip

# LICENSE

```
By using this software, you agree to the following conditions:
Use this software at your own risk. The program is provided as is without any guarantees or warranty.
Tinkerine Studio is not responsible for any damage to your machine (although highly unlikely) caused by the use of the software.

For questions, comments or feedback, feel free to email: support@tinkerines.com 

Coordia is open source software; you are free to distribute and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

For a copy of the GNU General Public License, see http://www.gnu.org/licenses/

```
