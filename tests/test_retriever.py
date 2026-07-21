import unittest

from sentinel_x.retrieval.retriever import KnowledgeRetriever


class KnowledgeRetrieverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.retriever = KnowledgeRetriever()

    def test_un1090_retrieval(self) -> None:
        result = self.retriever.retrieve(text="Incident label shows UN1090 near storage.")

        self.assertEqual("un_code", result.match_type)
        self.assertEqual("UN1090", result.matched_key)
        self.assertEqual("UN1090_acetone.json", result.filename)
        self.assertEqual("Acetone", result.record["name"])

    def test_flame_retrieval(self) -> None:
        result = self.retriever.retrieve(text="A flame symbol is visible on the container.")

        self.assertEqual("hazard_symbol", result.match_type)
        self.assertEqual("flame", result.matched_key)
        self.assertEqual("CLASS_3_FLAMMABLE.json", result.filename)
        self.assertEqual("Class 3 Flammable Liquid", result.record["name"])

    def test_unknown_fallback(self) -> None:
        result = self.retriever.retrieve(text="Unlabeled container with unclear residue.")

        self.assertEqual("unknown_fallback", result.match_type)
        self.assertEqual("UNKNOWN_HAZARD", result.matched_key)
        self.assertEqual("UNKNOWN_HAZARD.json", result.filename)
        self.assertEqual("Unknown Hazard", result.record["name"])


if __name__ == "__main__":
    unittest.main()
