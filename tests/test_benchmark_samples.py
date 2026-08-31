import pytest


@pytest.mark.benchmark(
    group="json",
    min_rounds=5,
)
def test_benchmark_json_parsing(benchmark):
    data = '{"items": [{"id": 1, "name": "test"}], "total": 1}'

    def parse():
        import json
        return json.loads(data)

    result = benchmark(parse)
    assert result["total"] == 1


@pytest.mark.benchmark(
    group="string-format",
    min_rounds=5,
)
def test_benchmark_f_string(benchmark):
    name, count = "benchmark", 42

    def format_string():
        return f"User: {name}, Count: {count}"

    result = benchmark(format_string)
    assert "benchmark" in result


@pytest.mark.benchmark
def test_benchmark_simple_arithmetic(benchmark):
    def add():
        return sum(range(1000))

    result = benchmark(add)
    assert result == 499500
