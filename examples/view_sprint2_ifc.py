"""
View Sprint 2 IFC file in OCP CAD Viewer.

This script loads the Sprint 2 demo IFC and displays it in the viewer.
"""

try:
    from ocp_vscode import show
    import ifcopenshell
    import ifcopenshell.geom

    print("Loading Sprint 2 IFC file...")
    ifc_file = ifcopenshell.open("examples/output/sprint2_demo.ifc")

    print(f"Schema: {ifc_file.schema}")
    print(f"Walls: {len(ifc_file.by_type('IfcWall'))}")
    print(f"Slabs: {len(ifc_file.by_type('IfcSlab'))}")
    print(f"Roofs: {len(ifc_file.by_type('IfcRoof'))}")

    # Create geometry settings (without Python OpenCASCADE)
    settings = ifcopenshell.geom.settings()

    # Collect all shapes
    shapes = []

    print("\nExtracting geometry from IFC...")

    # Get all product elements (walls, slabs, roofs)
    products = ifc_file.by_type("IfcProduct")

    for product in products:
        if product.is_a("IfcWall") or product.is_a("IfcSlab") or product.is_a("IfcRoof"):
            try:
                shape = ifcopenshell.geom.create_shape(settings, product)
                if shape:
                    # Convert triangulated mesh to OCP solid
                    from OCP.TopoDS import TopoDS_Compound, TopoDS_Shell
                    from OCP.BRep import BRep_Builder
                    from OCP.BRepBuilderAPI import (
                        BRepBuilderAPI_MakePolygon,
                        BRepBuilderAPI_MakeFace,
                        BRepBuilderAPI_Sewing
                    )
                    from OCP.gp import gp_Pnt

                    # Get triangulation data
                    geom = shape.geometry
                    verts = geom.verts  # Flat list of coordinates [x1,y1,z1, x2,y2,z2, ...]
                    faces = geom.faces  # Flat list of indices [i1,i2,i3, i4,i5,i6, ...]

                    # Use sewing to create a solid from triangles
                    sewing = BRepBuilderAPI_Sewing(1.0e-6)

                    # Process faces (groups of 3 indices)
                    for i in range(0, len(faces), 3):
                        idx1, idx2, idx3 = faces[i], faces[i+1], faces[i+2]

                        # Get vertex coordinates
                        p1 = gp_Pnt(verts[idx1*3], verts[idx1*3+1], verts[idx1*3+2])
                        p2 = gp_Pnt(verts[idx2*3], verts[idx2*3+1], verts[idx2*3+2])
                        p3 = gp_Pnt(verts[idx3*3], verts[idx3*3+1], verts[idx3*3+2])

                        # Create triangle face
                        polygon = BRepBuilderAPI_MakePolygon()
                        polygon.Add(p1)
                        polygon.Add(p2)
                        polygon.Add(p3)
                        polygon.Close()

                        if polygon.IsDone():
                            face_builder = BRepBuilderAPI_MakeFace(polygon.Wire())
                            if face_builder.IsDone():
                                sewing.Add(face_builder.Face())

                    # Perform sewing
                    sewing.Perform()
                    sewn_shape = sewing.SewedShape()

                    shapes.append(sewn_shape)
                    print(f"  ✓ {product.is_a()}: {product.Name}")
            except Exception as e:
                print(f"  ✗ Failed to create geometry for {product.Name}: {e}")

    if shapes:
        print(f"\nDisplaying {len(shapes)} elements in OCP CAD Viewer...")
        show(*shapes)
        print("✓ Geometry displayed in viewer!")
    else:
        print("\n⚠ No geometry found to display")
        print("Note: Geometry representation may not be fully implemented yet")

except ImportError as e:
    print(f"Error: {e}")
    print("\nRequired packages:")
    print("  - ocp-vscode (for viewer)")
    print("  - ifcopenshell (for IFC)")
    print("\nInstall with: pip install ocp-vscode ifcopenshell")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
