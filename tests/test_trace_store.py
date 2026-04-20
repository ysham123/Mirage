from concurrent.futures import ThreadPoolExecutor

from mirage.trace import TraceStore


def test_trace_store_appends_concurrently_without_corrupting_json(tmp_path):
    store = TraceStore(tmp_path)

    def append(index: int) -> None:
        store.append_event("concurrent-run", {"index": index})

    with ThreadPoolExecutor(max_workers=12) as executor:
        list(executor.map(append, range(100)))

    trace = store.read_trace("concurrent-run")

    assert len(trace["events"]) == 100
    assert sorted(event["index"] for event in trace["events"]) == list(range(100))
