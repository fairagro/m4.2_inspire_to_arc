from arctrl import ARC, ArcInvestigation, ArcStudy, ArcTable, CompositeHeader, CompositeCell, OntologyAnnotation
import json

print("CompositeCell dir:", dir(CompositeCell))

try:
    study = ArcStudy.create("study_id", "Study Title")
    table = ArcTable.init("Metadata Characteristics")
    
    # Header
    param_header = CompositeHeader.parameter(OntologyAnnotation("Spatial Extent"))
    
    # Cell: Try creating a Term cell instead of FreeText
    # If the value is just text, we can wrap it in OntologyAnnotation with Name=text
    cell = CompositeCell.term(OntologyAnnotation("10.0, 48.0, 11.0, 49.0"))
    
    table.AddColumn(param_header, [cell])
    print("Added Column successfully")
    
    study.AddTable(table)
    
    inv = ArcInvestigation.create("inv_id", "inv_title")
    inv.AddStudy(study)
    arc = ARC.from_arc_investigation(inv)
    
    json_str = arc.ToROCrateJsonString()
    data = json.loads(json_str)
    
    # Check JSON
    found = False
    for graph in data.get("@graph", []):
        # Look for the Parameter Value
        if "Spatial Extent" in str(graph):
             print("Found Spatial Extent in graph item:", graph.get("@type"), graph.get("name"))
             found = True
        if "10.0, 48.0, 11.0, 49.0" in str(graph):
             print("Found Value in graph item:", graph.get("@type"))
             found = True

    if not found:
        print("Spatial Extent/Value NOT found in JSON graph")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
