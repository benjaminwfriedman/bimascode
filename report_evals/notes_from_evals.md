Interesting things. The prompt is obviously important - in my first version of the prompts - I didn't specify anything about space to be left between windows and doors - and without that specificity - the agent placed a window and door overlapping. Simillarly, in eval 3, a wall terminated at a window - if its a non-load baring wall that could be okay, but regarless it was not my intention. Finally this issue also manifested in eval 5 where a structural column was placed in a door opening. Since both the tests and the generation are conditioned on the prompt - text checking was not scoped to block these issues either. Once I added a design constraints element in the prompt, these issues were remidied. This hints at the power this sort of system might have if it has access to applicable building codes for example. It also hints at the fact that world knowledge alone is not enough to encode these sorts of spatial conflicts. Even with the spatial conflicts - I observed that the tester agent didn't create tests to make sure interior walls didn't connect to exterior walls at wall openings, after notifying the agent, it was able to fix its mistake successfully.

Interesting note - on the two story building eval I specifically asked: "Make sure that there are ways to access each room via doors or openings." the tester decided "Doors - Checks minimum door counts for room access on each floor" which it wrote as simple door count checks - clearer prompting might improve this: 

```
class TestDoors:
    """Test door counts and placements."""

    def test_has_doors(self, ifc_path):
        """Building should have doors for room access."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        # Minimum: front door + doors to living room, kitchen, bedrooms, bathroom
        # At least 5-6 doors needed
        assert len(doors) >= 5, f"Expected at least 5 doors for room access, got {len(doors)}"

    def test_has_front_door(self, ifc_path):
        """Building should have at least one exterior door (front door in vestibule)."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        # At least one door should be present for the entry
        assert len(doors) >= 1, "Building needs at least a front door"

    def test_doors_on_ground_floor(self, ifc_path):
        """Ground floor should have doors (front door + room access)."""
        ifc = ifcopenshell.open(ifc_path)
        storeys = sorted(ifc.by_type("IfcBuildingStorey"), key=lambda s: s.Elevation or 0)

        ground_doors = get_elements_on_storey(ifc, "IfcDoor", storeys[0])
        # Ground floor needs: front door + access to living, kitchen
        assert len(ground_doors) >= 2, f"Ground floor should have at least 2 doors, got {len(ground_doors)}"

    def test_doors_on_upper_floor(self, ifc_path):
        """Upper floor should have doors (bedroom and bathroom access)."""
        ifc = ifcopenshell.open(ifc_path)
        storeys = sorted(ifc.by_type("IfcBuildingStorey"), key=lambda s: s.Elevation or 0)

        upper_doors = get_elements_on_storey(ifc, "IfcDoor", storeys[1])
        # Upper floor needs: master bedroom, second bedroom, bathroom
        assert len(upper_doors) >= 3, f"Upper floor should have at least 3 doors, got {len(upper_doors)}"


```


I tested builders with and without test access. In eval 2 I observed the agent with test access finding that its initial code didn't create multisheet pdfs, instead defaulting to a single sheet. To fix this it imported matplitlib and some pdf modules to create a pdf that satisfied the tests. In eval 3 the blind agent fogot to make sure that internal walls must not terminate in openings, the test aware agent did not make this same mistake but interestingly it didn't decided to directly test this, and might just demonstrate the stocasticity of agent decisions. 

In eval 5 structural grid for some reason the agent decides to test Columns don't conflict with doors, 
Beams don't conflict with windows. rather than testing that either don't conflict with either - another example of misunderstanding spatial requiements. However it did find the issue - on the tests run in the tests aware builder:

```
One test failed - there's a column at (12000, 0) that conflicts with the loading door centered at (10000, -50). The loading door is centered at X=12000 (center of the building is 24000/2 = 12000), so it conflicts with the column at that grid intersection.

I need to move the loading door so it doesn't conflict with the column grid. The columns are at X = 0, 6000, 12000, 18000, 24000. The loading door is 4m (4000mm) wide. I should center it between two grid lines instead.

Let me fix this by placing the loading door between columns, for example centered at X=9000 (between grid lines at 6000 and 12000).
```
It was able to pass its tests without actually fully removing the conflict. After being shown the issue visually it attempted again and after some back and forth prompting, the agent descovered that the test the test agent wrote was in correct and it fixed the issue while failing the tests. 

The build agent also did not pass wall heights to the walls, which was a mistake and after prompting fixed its mistake by explicity passing wall height into the wall objects. 