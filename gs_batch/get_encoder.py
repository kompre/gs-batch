import sys
import locale

# Pick a safe default encoding depending on platform
if sys.platform == "win32":
    # Windows uses the active codepage
    default_encoding = "mbcs"  # Python's alias for Windows ANSI codepage
else:
    # Linux / macOS typically use UTF-8
    default_encoding = locale.getpreferredencoding(False)