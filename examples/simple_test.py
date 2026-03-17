"""
Simplest possible visualization test.
"""

from build123d import Box
from ocp_vscode import show, set_port, set_defaults

# Configure viewer
set_defaults(reset_camera=True)

# Create a simple box
box = Box(1000, 1000, 1000)

# Show it
show(box)

print("✓ Box created and sent to viewer")
print("✓ Open the OCP CAD Viewer panel in VS Code:")
print("  1. Press Cmd+Shift+P")
print("  2. Type 'OCP CAD Viewer: Show'")
print("  3. Press Enter")
