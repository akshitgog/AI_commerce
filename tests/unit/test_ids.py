from ai_commerce_gateway.core.ids import new_id


def test_ids_are_opaque_prefixed_and_unique() -> None:
    first = new_id("txn")
    second = new_id("txn")
    assert first.startswith("txn_")
    assert first != second
