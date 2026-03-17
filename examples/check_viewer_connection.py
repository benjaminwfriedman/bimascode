"""
Check if OCP CAD Viewer is ready to receive connections.
"""

import socket

def check_port(port=3939):
    """Check if the viewer is listening on the port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        result = s.connect_ex(('127.0.0.1', port))
        s.close()
        return result == 0
    except:
        return False

print("Checking OCP CAD Viewer connection...")
print(f"Looking for viewer on 127.0.0.1:3939...")

if check_port(3939):
    print("✓ Viewer is listening!")
    print("\nNow run: python examples/quick_viz.py")
else:
    print("✗ Viewer is NOT listening on port 3939")
    print("\nTo fix this:")
    print("1. In VS Code, press Cmd+Shift+P")
    print("2. Type 'OCP CAD Viewer: Show'")
    print("3. The viewer panel should open")
    print("4. Run this check again")
    print("\nOR: The viewer might start automatically when you call show()")
    print("     Try running: python examples/quick_viz.py anyway")
