import unittest
from middleware.inspire_to_arc.mapper import InspireMapper
from middleware.inspire_to_arc.harvester import InspireRecord
from arctrl import ARC

class TestInspireMapper(unittest.TestCase):
    
    def setUp(self):
        self.mapper = InspireMapper()
        self.record = InspireRecord(
            identifier="uuid-123",
            title="Test Dataset",
            abstract="A test dataset description",
            date_stamp="2023-10-27",
            keywords=["keyword1", "keyword2"],
            topic_categories=["biota"],
            contacts=[
                {"name": "John Doe", "organization": "Test Org", "email": "john@example.com", "role": "author", "type": "resource"}
            ],
            lineage="Processed using algorithm X",
            spatial_extent=[10.0, 48.0, 11.0, 49.0],
            temporal_extent=("2020-01-01", "2020-12-31"),
            constraints=["Public Domain"]
        )

    def test_map_record_structure(self):
        arc = self.mapper.map_record(self.record)
        
        self.assertIsInstance(arc, ARC)
        self.assertEqual(arc.Identifier, "uuid-123")
        self.assertEqual(arc.Title, "Test Dataset")
        self.assertEqual(arc.Description, "A test dataset description")
        self.assertEqual(arc.SubmissionDate, "2023-10-27")
        
        # Check Contacts
        self.assertEqual(len(arc.Contacts), 1)
        contact = arc.Contacts[0]
        self.assertEqual(contact.LastName, "Doe")
        self.assertEqual(contact.FirstName, "John")
        self.assertEqual(contact.Affiliation, "Test Org")
        
    def test_map_study_and_tables(self):
        arc = self.mapper.map_record(self.record)
        
        # Check Study
        self.assertEqual(len(arc.Studies), 1)
        study = arc.Studies[0]
        self.assertEqual(study.Identifier, "uuid-123_study")
        self.assertEqual(study.Description, "Processed using algorithm X")
        
        # Check Table (Extended Metadata)
        self.assertEqual(len(study.Tables), 1)
        table = study.Tables[0]
        self.assertEqual(table.Name, "Metadata Characteristics")
        
        # Check Columns/Headers
        # We expect 3 columns: Spatial Extent, Temporal Extent, Access Constraints
        self.assertEqual(table.ColumnCount, 3)
        
        # Verify Headers
        headers = [col.Header.ToTerm().Name for col in table.Columns]
        self.assertIn("Spatial Extent", headers)
        self.assertIn("Temporal Extent", headers)
        self.assertIn("Access Constraints", headers)
        
        # Verify Values (Cells)
        # We need to find the column for "Spatial Extent" and check its cell
        spatial_col = next(col for col in table.Columns if col.Header.ToTerm().Name == "Spatial Extent")
        self.assertEqual(len(spatial_col.Cells), 1)
        # The cell value is wrapped in OntologyAnnotation, we check the Name
        self.assertEqual(spatial_col.Cells[0].AsTerm.Name, "[10.0, 48.0, 11.0, 49.0]")

    def test_map_assay(self):
        arc = self.mapper.map_record(self.record)
        
        self.assertEqual(len(arc.Assays), 1)
        assay = arc.Assays[0]
        self.assertEqual(assay.Identifier, "uuid-123_assay")
        self.assertEqual(assay.MeasurementType.TermName, "biota")

if __name__ == "__main__":
    unittest.main()
