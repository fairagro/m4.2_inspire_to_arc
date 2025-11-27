import unittest
from unittest.mock import MagicMock, patch
from middleware.inspire_to_arc.harvester import CSWClient, InspireRecord
from owslib.iso import MD_Metadata

class TestCSWClient(unittest.TestCase):
    
    @patch("middleware.inspire_to_arc.harvester.CatalogueServiceWeb")
    def test_connect(self, mock_csw):
        client = CSWClient("http://example.com/csw")
        client.connect()
        mock_csw.assert_called_with("http://example.com/csw", timeout=30)
        self.assertIsNotNone(client.csw)

    @patch("middleware.inspire_to_arc.harvester.CatalogueServiceWeb")
    def test_get_records(self, mock_csw_cls):
        # Setup mock CSW
        mock_csw_instance = MagicMock()
        mock_csw_cls.return_value = mock_csw_instance
        
        # Mock records
        mock_record = MagicMock(spec=MD_Metadata)
        mock_record.identifier = "uuid-123"
        # Configure nested mocks
        mock_identification = MagicMock()
        mock_identification.title = "Test Title"
        mock_identification.abstract = "Test Abstract"
        mock_identification.keywords = []
        mock_identification.topiccategory = ["biota"]
        mock_identification.contact = []
        mock_identification.bbox = None
        mock_identification.temporalextent_start = None
        mock_record.identification = mock_identification
        
        mock_record.datestamp = "2023-01-01"
        mock_record.contact = []
        
        mock_dataquality = MagicMock()
        mock_lineage = MagicMock()
        mock_lineage.statement = "Test Lineage"
        mock_dataquality.lineage = mock_lineage
        mock_record.dataquality = mock_dataquality
        
        mock_csw_instance.records = {"uuid-123": mock_record}
        mock_csw_instance.results = {'matches': 1}
        
        client = CSWClient("http://example.com/csw")
        records = list(client.get_records(max_records=1))
        
        self.assertEqual(len(records), 1)
        self.assertIsInstance(records[0], InspireRecord)
        self.assertEqual(records[0].identifier, "uuid-123")
        self.assertEqual(records[0].title, "Test Title")
        self.assertEqual(records[0].lineage, "Test Lineage")

if __name__ == "__main__":
    unittest.main()
