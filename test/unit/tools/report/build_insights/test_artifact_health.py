"""Unit tests for build-insights Artifact Health compute functions.
Pure-function tests against fabricated build records -- no HTTP involved."""

from src.tools.report.build_insights.artifact_health import (
    _primary_artifact_size,
    artifact_size_per_profile,
    biggest_grower_and_shrinker,
)


def _build(profile="A", status=0, target_file=None, artifact_items=None):
    return {
        "buildProfileName": profile,
        "buildStatus": status,
        "targetFile": target_file,
        "artifactItems": artifact_items or [],
    }


class TestPrimaryArtifactSize:
    def test_uses_target_file_when_present(self):
        build = _build(target_file={"filename": "app.ipa", "fileSize": 40.0})
        assert _primary_artifact_size(build) == 40.0

    def test_falls_back_to_largest_artifact_item_when_target_file_is_null(self):
        build = _build(artifact_items=[
            {"filename": "app.aab", "fileSize": 20.0},
            {"filename": "app-debug.aab", "fileSize": 35.0},
        ])
        assert _primary_artifact_size(build) == 35.0

    def test_excludes_non_artifact_metadata_files(self):
        build = _build(artifact_items=[
            {"filename": "build_metadata.json", "fileSize": 999.0},
            {"filename": "ExportOptions.plist", "fileSize": 999.0},
            {"filename": "Packaging.log", "fileSize": 999.0},
            {"filename": "release-notes.txt", "fileSize": 999.0},
        ])
        assert _primary_artifact_size(build) is None

    def test_recognizes_each_installable_artifact_type(self):
        for filename in ("app.ipa", "app.apk", "app.aab"):
            build = _build(artifact_items=[{"filename": filename, "fileSize": 12.0}])
            assert _primary_artifact_size(build) == 12.0

    def test_extension_match_is_case_insensitive(self):
        build = _build(artifact_items=[{"filename": "app.IPA", "fileSize": 12.0}])
        assert _primary_artifact_size(build) == 12.0

    def test_unrecognized_new_metadata_format_is_not_mistaken_for_an_artifact(self):
        """A future metadata format the API might add (e.g. a new report
        file) should never be silently treated as the primary artifact --
        this is the whole point of whitelisting installable extensions
        instead of blacklisting known metadata ones."""
        build = _build(artifact_items=[{"filename": "future-report.newformat", "fileSize": 999.0}])
        assert _primary_artifact_size(build) is None

    def test_no_artifact_items_returns_none(self):
        assert _primary_artifact_size(_build()) is None


class TestArtifactSizePerProfile:
    def test_averages_current_period_sizes(self):
        curr = [
            _build(profile="A", target_file={"filename": "app.ipa", "fileSize": 40.0}),
            _build(profile="A", target_file={"filename": "app.ipa", "fileSize": 44.0}),
        ]
        rows = artifact_size_per_profile(curr, [], ["A"])
        assert rows[0]["current_avg_size_mb"] == 42.0

    def test_skips_profile_with_no_current_artifacts(self):
        curr = [_build(profile="A", status=1)]  # failed, excluded
        assert artifact_size_per_profile(curr, [], ["A"]) == []

    def test_delta_is_none_with_no_previous_baseline(self):
        curr = [_build(profile="A", target_file={"filename": "app.ipa", "fileSize": 40.0})]
        rows = artifact_size_per_profile(curr, [], ["A"])
        assert rows[0]["prev_avg_size_mb"] is None
        assert rows[0]["delta_mb"] is None
        assert rows[0]["delta_pct"] is None

    def test_delta_mb_and_pct_computed_against_previous_period(self):
        curr = [_build(profile="A", target_file={"filename": "app.ipa", "fileSize": 44.0})]
        prev = [_build(profile="A", target_file={"filename": "app.ipa", "fileSize": 40.0})]
        rows = artifact_size_per_profile(curr, prev, ["A"])
        assert rows[0]["delta_mb"] == 4.0
        assert rows[0]["delta_pct"] == 10.0

    def test_sorted_by_current_avg_size_descending(self):
        curr = [
            _build(profile="A", target_file={"filename": "a.ipa", "fileSize": 10.0}),
            _build(profile="B", target_file={"filename": "b.ipa", "fileSize": 50.0}),
        ]
        rows = artifact_size_per_profile(curr, [], ["A", "B"])
        assert [r["profile"] for r in rows] == ["B", "A"]

    def test_failed_builds_excluded_from_averages(self):
        curr = [
            _build(profile="A", status=0, target_file={"filename": "a.ipa", "fileSize": 10.0}),
            _build(profile="A", status=1, target_file={"filename": "a.ipa", "fileSize": 999.0}),
        ]
        rows = artifact_size_per_profile(curr, [], ["A"])
        assert rows[0]["current_avg_size_mb"] == 10.0


class TestBiggestGrowerAndShrinker:
    def test_identifies_grower_and_shrinker(self):
        rows = [
            {"profile": "A", "delta_mb": 5.0},
            {"profile": "B", "delta_mb": -3.0},
            {"profile": "C", "delta_mb": 1.0},
        ]
        result = biggest_grower_and_shrinker(rows)
        assert result["grower"]["profile"] == "A"
        assert result["shrinker"]["profile"] == "B"

    def test_no_grower_when_all_stable_or_shrinking(self):
        rows = [{"profile": "A", "delta_mb": -2.0}]
        assert biggest_grower_and_shrinker(rows)["grower"] is None

    def test_no_shrinker_when_all_stable_or_growing(self):
        rows = [{"profile": "A", "delta_mb": 2.0}]
        assert biggest_grower_and_shrinker(rows)["shrinker"] is None

    def test_profiles_with_no_baseline_never_qualify(self):
        rows = [{"profile": "A", "delta_mb": None}]
        result = biggest_grower_and_shrinker(rows)
        assert result["grower"] is None
        assert result["shrinker"] is None

    def test_both_none_when_no_rows(self):
        result = biggest_grower_and_shrinker([])
        assert result == {"grower": None, "shrinker": None}
