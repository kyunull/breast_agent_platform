from app.extraction.schemas import ExtractionConfig
from app.extraction.service import preview_extraction


def test_preview_groups_path_values_and_latest_array_record():
    payload = {
        "院内数据": {
            "住院文书": [
                {"日期": "2026-01-01", "类型": "病程", "文本": "旧"},
                {"日期": "2026-01-03", "类型": "病程", "文本": "新"},
            ]
        },
        "病理": {"HER2": "IHC 3+"},
    }
    config = ExtractionConfig.model_validate(
        {
            "groups": [
                {
                    "id": "baseline",
                    "label": "基线资料",
                    "required": ["her2"],
                    "fields": [
                        {"alias": "her2", "path": "$.病理.HER2", "type": "string"},
                        {
                            "alias": "latest_record",
                            "path": "$.院内数据.住院文书",
                            "type": "object",
                            "array": {"take": "latest", "sort_by": "日期"},
                        },
                    ],
                }
            ]
        }
    )

    result = preview_extraction(payload, config)

    assert result.groups["baseline"]["her2"] == "IHC 3+"
    assert result.groups["baseline"]["latest_record"]["文本"] == "新"
    assert result.sufficiency["baseline"].status == "sufficient"


def test_preview_reports_missing_required_field():
    config = ExtractionConfig.model_validate(
        {
            "groups": [
                {
                    "id": "pathology",
                    "label": "病理信息",
                    "required": ["er"],
                    "fields": [{"alias": "er", "path": "$.病理.ER", "type": "string"}],
                }
            ]
        }
    )
    result = preview_extraction({}, config)
    assert result.missing["pathology"] == ["er"]
    assert result.sufficiency["pathology"].status == "insufficient"


def test_array_filter_time_window_and_all_preserve_order():
    payload = {
        "records": [
            {"date": "2026-01-01", "type": "course", "text": "old"},
            {"date": "2026-01-02", "type": "other", "text": "skip"},
            {"date": "2026-01-03", "type": "course", "text": "new"},
        ]
    }
    config = ExtractionConfig.model_validate(
        {
            "groups": [
                {
                    "id": "records",
                    "label": "记录",
                    "fields": [
                        {
                            "alias": "items",
                            "path": "$.records",
                            "type": "array",
                            "array": {
                                "filter": {"type": "course"},
                                "sort_by": "date",
                                "take": "all",
                                "time_from": "2026-01-02",
                            },
                        }
                    ],
                }
            ]
        }
    )
    result = preview_extraction(payload, config)
    assert [item["text"] for item in result.groups["records"]["items"]] == ["new"]


def test_default_type_error_and_invalid_path_are_reported_per_field():
    config = ExtractionConfig.model_validate(
        {
            "groups": [
                {
                    "id": "mixed",
                    "label": "混合",
                    "required": ["bad_type"],
                    "fields": [
                        {"alias": "defaulted", "path": "$.missing", "type": "string", "default": "暂无"},
                        {"alias": "bad_type", "path": "$.age", "type": "integer"},
                        {"alias": "invalid", "path": "$.[", "type": "string"},
                    ],
                }
            ]
        }
    )
    result = preview_extraction({"age": "forty"}, config)
    assert result.groups["mixed"]["defaulted"] == "暂无"
    assert result.missing["mixed"] == ["bad_type"]
    assert "bad_type" in result.errors["mixed"]
    assert "invalid" in result.errors["mixed"]


def test_array_sort_errors_are_reported_without_aborting_other_fields():
    config = ExtractionConfig.model_validate(
        {
            "groups": [
                {
                    "id": "records",
                    "label": "记录",
                    "fields": [
                        {
                            "alias": "latest",
                            "path": "$.records",
                            "type": "object",
                            "array": {"take": "latest", "sort_by": "missing_date"},
                        },
                        {"alias": "name", "path": "$.name", "type": "string"},
                    ],
                }
            ]
        }
    )
    result = preview_extraction({"records": [{"text": "one"}], "name": "patient"}, config)
    assert result.groups["records"]["name"] == "patient"
    assert "latest" in result.errors["records"]


def test_extraction_preview_route_accepts_sample_json(client, medical_token):
    response = client.post(
        "/api/v1/workflows/demo/draft/extraction/preview",
        headers={"Authorization": f"Bearer {medical_token}"},
        json={
            "sample_json": {"病理": {"HER2": "IHC 3+"}},
            "config": {
                "groups": [
                    {
                        "id": "pathology",
                        "label": "病理",
                        "required": ["her2"],
                        "fields": [{"alias": "her2", "path": "$.病理.HER2", "type": "string"}],
                    }
                ]
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["groups"]["pathology"]["her2"] == "IHC 3+"
