from data_migration_harness.tools.mongo_reader import describe_collection, list_collections, sample


def test_list_collections_includes_products():
    assert "products" in list_collections()


def test_describe_collection_returns_field_summary():
    summary = describe_collection("products")
    assert "name" in summary["fields"]
    assert "reviews" in summary["fields"]


def test_sample_returns_documents():
    docs = sample("products", n=3)
    assert len(docs) == 3
    assert "name" in docs[0]
