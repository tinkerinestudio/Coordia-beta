# A setup script showing advanced features.
#
# Note that for the NT service to build correctly, you need at least
# win32all build 161, for the COM samples, you need build 163.
# Requires wxPython, and Tim Golden's WMI module.

# Note: WMI is probably NOT a good example for demonstrating how to
# include a pywin32 typelib wrapper into the exe: wmi uses different
# typelib versions on win2k and winXP.  The resulting exe will only
# run on the same windows version as the one used to build the exe.
# So, the newest version of wmi.py doesn't use any typelib anymore.

###NOTE TO SELF###
#You have to put in the skeinforge folder in dist/lib/shared.zip and fabmetheus_utilities+skeinforge_application into dist for it to work!
#Also include: coordia.ico, msvcp71.dll, msvcp90.dll, python27.dll
#Also put python27.dll into python
#Also put images into dist and lib

from distutils.core import setup
import py2exe
import sys

# If run without args, build executables, in quiet mode.
if len(sys.argv) == 1:
    sys.argv.append("py2exe")
    sys.argv.append("-q")

class Target:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        # for the versioninfo resources
        self.version = "0.2.2"
        self.company_name = "Tinkerine Studio"
        self.copyright = "no copyright"
        self.name = "Coordia0.2.2"

################################################################
# A program using wxPython

# The manifest will be inserted as resource into test_wx.exe.  This
# gives the controls the Windows XP appearance (if run on XP ;-)
#
# Another option would be to store it in a file named
# test_wx.exe.manifest, and copy it with the data_files option into
# the dist-dir.
#

manifest_template = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity
    version="5.0.0.0"
    processorArchitecture="x86"
    name="%(prog)s"
    type="win32"
  />
  <description>%(prog)s</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel
            level="asInvoker"
            uiAccess="false">
        </requestedExecutionLevel>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity
            type="win32"
            name="Microsoft.VC90.CRT"
            version="9.0.21022.8"
            processorArchitecture="x86"
            publicKeyToken="1fc8b3b9a1e18e3b">
      </assemblyIdentity>
    </dependentAssembly>
  </dependency>
  <dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="X86"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
  </dependency>
</assembly>
"""

RT_MANIFEST = 24

Coordia = Target(
    # used for the versioninfo resource
    description = "Coordia 0.2.2",

    # what to build
    script = "Coordia.py",
    other_resources = [(RT_MANIFEST, 1, manifest_template % dict(prog="Coordia"))],
    icon_resources = [(1, "coordia.ico")],
    dest_base = "Coordia")

test_wx_console = Target(
    # used for the versioninfo resource
    description = "A sample GUI app with console blah!",

    # what to build
    script = "pronterface.py",
    other_resources = [(RT_MANIFEST, 1, manifest_template % dict(prog="test_wx"))],
    dest_base = "test_wx_console")

################################################################
# A program using early bound COM, needs the typelibs option below
test_wmi = Target(
    description = "Early bound COM client example",
    script = "test_wmi.py",
    )

################################################################
# a NT service, modules is required
myservice = Target(
    # used for the versioninfo resource
    description = "A sample Windows NT service",
    # what to build.  For a service, the module name (not the
    # filename) must be specified!
    modules = ["MyService"]
    )

################################################################
# a COM server (exe and dll), modules is required
#
# If you only want a dll or an exe, comment out one of the create_xxx
# lines below.

interp = Target(
    description = "Python Interpreter as COM server module",
    # what to build.  For COM servers, the module name (not the
    # filename) must be specified!
    modules = ["win32com.servers.interp"],
##    create_exe = False,
##    create_dll = False,
    )

################################################################
# COM pulls in a lot of stuff which we don't want or need.

excludes = ["pywin", "pywin.debugger", "pywin.debugger.dbgcon",
            "pywin.dialogs", "pywin.dialogs.list"]

setup(
    options = {"py2exe": {"typelibs":
                          # typelib for WMI
                          [('{565783C6-CB41-11D1-8B02-00600806D9B6}', 0, 1, 2)],
                          # create a compressed zip archive
                          "compressed": 1,
                          "optimize": 0,
                          "excludes": excludes,
                          "dll_excludes": [ "MSVCP90.dll","python25.dll" ]  }},
    # The lib directory contains everything except the executables and the python dll.
    # Can include a subdirectory name.
    zipfile = "lib/shared.zip",

    #service = [myservice],
    #com_server = [interp],
    #console = [test_wx_console, test_wmi],
    windows = [Coordia],
    )
