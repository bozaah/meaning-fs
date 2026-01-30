"""
Tests for directory context inference.
"""

from meaning.meaning_inference import (
    InferredIntent,
    infer_intent_from_directory_context,
)


def test_infer_context_simple_config():
    # src/app/configs/settings.json
    intent = infer_intent_from_directory_context("src/app/configs/settings.json")
    assert intent is not None
    assert intent.intent == "Configuration files for app."
    assert intent.confidence == 0.8


def test_infer_context_deep_data():
    # src/modules/weather/data/raw/observations.csv
    # Should pick up "data" marker and "weather" context (skipping 'modules')
    # logic:
    # parts: src, modules, weather, data, raw, observations.csv
    # iteration: raw (no), data (yes)
    # marker: data -> "Data files"
    # context check: parent is "weather". "weather" is not in excluded set. context="weather"
    intent = infer_intent_from_directory_context("src/modules/weather/data/raw/observations.csv")
    assert intent is not None
    assert intent.intent == "Data files for weather."


def test_infer_context_root_config():
    # config/app.yaml
    intent = infer_intent_from_directory_context("config/app.yaml")
    assert intent is not None
    assert intent.intent == "Configuration files."


def test_infer_context_test_files():
    # tests/test_files/integration/output.json
    intent = infer_intent_from_directory_context("tests/test_files/integration/output.json")
    assert intent is not None
    assert intent.intent == "Test output data for integration."


def test_infer_context_fixtures_in_tests():
    # tests/fixtures/users.json
    intent = infer_intent_from_directory_context("tests/fixtures/users.json")
    assert intent is not None
    # parent is 'tests' which is excluded, so grand parent? 'tests' is index 0.
    # parts: tests, fixtures, users.json
    # i=1 (fixtures). parent=tests. excluded. i=1. grandparent check? i>1 is False.
    # so context is None.
    assert intent.intent == "Test fixture data."


def test_infer_context_model_definitions():
    # src/domain/models/user.py
    intent = infer_intent_from_directory_context("src/domain/models/user.py")
    assert intent is not None
    assert intent.intent == "Model definitions for domain."
