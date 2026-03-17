"""
Minimal test to verify OCP CAD Viewer connection.
"""

from build123d import Box
from ocp_vscode import show, reset_show, set_defaults

print("Testing OCP CAD Viewer connection...")

# Reset viewer
reset_show()

# Configure
set_defaults(reset_camera=True)

# Create a simple box
box = Box(1000, 1000, 1000)

print("Sending geometry to viewer...")
show(box)

print("✓ Geometry sent!")
print("\nCheck the OCP CAD Viewer panel - you should see a cube.")
print("If not, try:")
print("  1. Make sure the OCP CAD Viewer panel is visible")
print("  2. Run this script again")
print("  3. Check the OCP CAD Viewer Log for errors")
