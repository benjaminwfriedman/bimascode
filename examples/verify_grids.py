"""
Verify grid lines in IFC files and visualize them.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import ifcopenshell
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def verify_ifc_grids(ifc_path):
    """
    Verify grid lines exist in an IFC file and show their structure.

    Args:
        ifc_path: Path to IFC file
    """
    print(f"\n{'='*70}")
    print(f"Verifying: {Path(ifc_path).name}")
    print(f"{'='*70}\n")

    # Open IFC file
    ifc_file = ifcopenshell.open(ifc_path)

    # Check for IfcGrid entities
    grids = ifc_file.by_type("IfcGrid")
    print(f"✓ Found {len(grids)} IfcGrid entity/entities")

    if not grids:
        print("  ⚠ No grids found in IFC file")
        return []

    all_grid_lines = []

    for grid in grids:
        print(f"\n  Grid: {grid.Name}")
        print(f"  Description: {grid.Description}")
        print(f"  GUID: {grid.GlobalId}")

        # Check U axes (typically vertical)
        if grid.UAxes:
            print(f"\n  U Axes (Vertical): {len(grid.UAxes)}")
            for axis in grid.UAxes:
                print(f"    - {axis.AxisTag}: {axis.AxisCurve}")
                if hasattr(axis.AxisCurve, 'Points'):
                    points = [(p.Coordinates[0], p.Coordinates[1]) for p in axis.AxisCurve.Points]
                    print(f"      Points: {points}")
                    all_grid_lines.append({
                        'label': axis.AxisTag,
                        'type': 'U',
                        'points': points
                    })

        # Check V axes (typically horizontal)
        if grid.VAxes:
            print(f"\n  V Axes (Horizontal): {len(grid.VAxes)}")
            for axis in grid.VAxes:
                print(f"    - {axis.AxisTag}: {axis.AxisCurve}")
                if hasattr(axis.AxisCurve, 'Points'):
                    points = [(p.Coordinates[0], p.Coordinates[1]) for p in axis.AxisCurve.Points]
                    print(f"      Points: {points}")
                    all_grid_lines.append({
                        'label': axis.AxisTag,
                        'type': 'V',
                        'points': points
                    })

        # Check W axes (for 3D grids)
        if grid.WAxes:
            print(f"\n  W Axes: {len(grid.WAxes)}")

    print(f"\n  ✓ Total grid axes: {len(all_grid_lines)}")

    return all_grid_lines


def plot_grids(grid_lines, title):
    """
    Create a 2D plot of grid lines.

    Args:
        grid_lines: List of grid line dictionaries
        title: Plot title
    """
    if not grid_lines:
        print("  No grid lines to plot")
        return

    fig, ax = plt.subplots(figsize=(12, 10))

    # Plot U axes (vertical) in blue
    u_count = 0
    v_count = 0

    for grid in grid_lines:
        points = grid['points']
        if len(points) < 2:
            continue

        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]

        if grid['type'] == 'U':
            color = 'blue'
            u_count += 1
            ax.plot(x_coords, y_coords, color=color, linewidth=2, marker='o')
            # Label at midpoint
            mid_x = (points[0][0] + points[1][0]) / 2
            mid_y = (points[0][1] + points[1][1]) / 2
            ax.text(mid_x, mid_y + 300, grid['label'],
                   fontsize=12, fontweight='bold', color='blue',
                   ha='center', va='bottom',
                   bbox=dict(boxstyle='circle', facecolor='white', edgecolor='blue'))
        else:  # V axis
            color = 'red'
            v_count += 1
            ax.plot(x_coords, y_coords, color=color, linewidth=2, marker='o')
            # Label at midpoint
            mid_x = (points[0][0] + points[1][0]) / 2
            mid_y = (points[0][1] + points[1][1]) / 2
            ax.text(mid_x + 300, mid_y, grid['label'],
                   fontsize=12, fontweight='bold', color='red',
                   ha='left', va='center',
                   bbox=dict(boxstyle='circle', facecolor='white', edgecolor='red'))

    # Add legend
    u_patch = mpatches.Patch(color='blue', label=f'U Axes (Vertical): {u_count}')
    v_patch = mpatches.Patch(color='red', label=f'V Axes (Horizontal): {v_count}')
    ax.legend(handles=[u_patch, v_patch], loc='upper right', fontsize=10)

    ax.set_xlabel('X (mm)', fontsize=12)
    ax.set_ylabel('Y (mm)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_aspect('equal')

    plt.tight_layout()
    return fig


if __name__ == "__main__":
    # Verify both example files
    examples_dir = Path(__file__).parent / "output"

    # File 1
    ifc_file_1 = examples_dir / "grid_example.ifc"
    if ifc_file_1.exists():
        grid_lines_1 = verify_ifc_grids(ifc_file_1)
        if grid_lines_1:
            fig1 = plot_grids(grid_lines_1, "Grid Example 1: 3x3 Grid")
            output_png_1 = examples_dir / "grid_example_viz.png"
            fig1.savefig(output_png_1, dpi=150)
            print(f"\n  ✓ Saved visualization: {output_png_1}")
            plt.close(fig1)
    else:
        print(f"File not found: {ifc_file_1}")

    # File 2
    ifc_file_2 = examples_dir / "grid_example_2.ifc"
    if ifc_file_2.exists():
        grid_lines_2 = verify_ifc_grids(ifc_file_2)
        if grid_lines_2:
            fig2 = plot_grids(grid_lines_2, "Grid Example 2: 4x3 Grid")
            output_png_2 = examples_dir / "grid_example_2_viz.png"
            fig2.savefig(output_png_2, dpi=150)
            print(f"\n  ✓ Saved visualization: {output_png_2}")
            plt.close(fig2)
    else:
        print(f"File not found: {ifc_file_2}")

    print(f"\n{'='*70}")
    print("✓ Grid verification complete!")
    print(f"{'='*70}\n")
