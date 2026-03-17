"""
OCP CAD Viewer setup and connection test.

This will help diagnose and fix the viewer connection.
"""

import sys
print(f"Python: {sys.executable}")
print(f"Python version: {sys.version}")

# Check if ocp_vscode is installed
try:
    import ocp_vscode
    print(f"✓ ocp_vscode installed: {ocp_vscode.__file__}")
except ImportError as e:
    print(f"✗ ocp_vscode not found: {e}")
    sys.exit(1)

# Check if build123d is installed
try:
    import build123d
    print(f"✓ build123d installed: {build123d.__file__}")
except ImportError as e:
    print(f"✗ build123d not found: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("Testing OCP CAD Viewer Connection")
print("="*60)

from build123d import Box
from ocp_vscode import show, set_port, set_defaults, reset_show

# Try to set up the viewer
print("\n1. Configuring viewer...")
try:
    set_defaults(
        reset_camera=True,
        axes=True,
        axes0=True,
        grid=[True, True, True],
        ortho=True,
    )
    print("   ✓ Viewer configured")
except Exception as e:
    print(f"   ✗ Configuration failed: {e}")

# Reset the viewer
print("\n2. Resetting viewer...")
try:
    reset_show()
    print("   ✓ Viewer reset")
except Exception as e:
    print(f"   ✗ Reset failed: {e}")

# Create simple geometry
print("\n3. Creating geometry...")
try:
    box = Box(1000, 1000, 1000)
    print("   ✓ Box created (1000x1000x1000)")
except Exception as e:
    print(f"   ✗ Geometry creation failed: {e}")
    sys.exit(1)

# Try to show it
print("\n4. Sending to viewer...")
try:
    show(box)
    print("   ✓ Geometry sent to viewer!")
except Exception as e:
    print(f"   ✗ Show failed: {e}")
    print(f"   Error type: {type(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("If you see '✓ Geometry sent to viewer!' above,")
print("check the OCP CAD Viewer panel in VS Code.")
print("\nTo open the viewer:")
print("  1. Press Cmd+Shift+P")
print("  2. Type 'OCP CAD Viewer: Show'")
print("  3. Select it")
print("\nYou should see a 1x1x1 meter cube.")
print("="*60)
