import unittest

from releasetasks.test.firefox import make_task_graph, do_common_assertions, \
    get_task_by_name, create_firefox_test_args
from releasetasks.test import PVT_KEY_FILE
from voluptuous import Schema
from voluptuous.humanize import validate_with_humanized_errors

EN_US_CONFIG = {
    "platforms": {
        "macosx64": {"task_id": "xyz"},
        "win32": {"task_id": "xyy"}
    }
}


L10N_CONFIG = {
    "platforms": {
        "win32": {
            "en_us_binary_url": "https://queue.taskcluster.net/something/firefox.exe",
            "locales": ["de", "en-GB", "zh-TW"],
            "chunks": 1,
        },
        "macosx64": {
            "en_us_binary_url": "https://queue.taskcluster.net/something/firefox.tar.xz",
            "locales": ["de", "en-GB", "zh-TW"],
            "chunks": 1,
        },

    },
    "changesets": {
        "de": "default",
        "en-GB": "default",
        "zh-TW": "default",
    },
}


class TestPushToMirrorsHuman(unittest.TestCase):
    maxDiff = 30000
    graph = None
    # we will end up with one task for each platform
    tasks = None
    human_task_name = "release-{}_{}_push_to_releases_human_decision".format("mozilla-beta",
                                                                             "firefox")
    HUMAN_TASK_SCHEMA = Schema({
        'task': {
            'provisionerId': 'null-provisioner',
            'workerType': 'human-decision',
        }
    }, extra=True, required=True)

    TASK_SCHEMA = Schema({
        'task': {
            'provisionerId': 'aws-provisioner-v1',
            'workerType': 'opt-linux64',
        }
    }, extra=True, required=True)

    def setUp(self):
        test_kwargs = create_firefox_test_args({
            'checksums_enabled': True,
            'updates_enabled': True,
            'push_to_candidates_enabled': True,
            'push_to_releases_enabled': True,
            'branch': 'mozilla-beta',
            'repo_path': 'releases/mozilla-beta',
            'signing_pvt_key': PVT_KEY_FILE,
            'release_channels': ['beta', 'release'],
            'final_verify_channels': ['beta', 'release'],
            'partner_repacks_platforms': ['win32', 'macosx64'],
            'en_US_config': EN_US_CONFIG,
            'l10n_config': L10N_CONFIG,
        })
        self.graph = make_task_graph(**test_kwargs)
        self.task = get_task_by_name(
            self.graph, "release-{}_{}_push_to_releases".format("mozilla-beta", "firefox")
        )
        self.human_task = get_task_by_name(self.graph, self.human_task_name)

    def test_common_assertions(self):
        do_common_assertions(self.graph)

    def test_task_schema(self):
        assert validate_with_humanized_errors(self.task, TestPushToMirrorsHuman.TASK_SCHEMA)

    def test_human_task_schema(self):
        assert validate_with_humanized_errors(self.human_task, TestPushToMirrorsHuman.HUMAN_TASK_SCHEMA)

    def test_scopes_present(self):
        self.assertFalse("scopes" in self.task["task"])

    def test_graph_scopes(self):
        expected_graph_scopes = set([
            "queue:task-priority:high",
            "queue:define-task:aws-provisioner-v1/opt-linux64",
            "queue:create-task:aws-provisioner-v1/opt-linux64"
        ])
        self.assertTrue(expected_graph_scopes.issubset(self.graph["scopes"]))

    def test_version_in_command(self):
        command = self.task['task']['payload']['command']
        self.assertTrue("--version 42.0b2" in "".join(command))

    def test_build_num_in_command(self):
        command = self.task['task']['payload']['command']
        self.assertTrue("--build-number 3" in "".join(command))

    def test_requires(self):
        requires = [get_task_by_name(self.graph, self.human_task_name)["taskId"]]
        self.assertEqual(self.task["requires"], requires)

    def test_human_requires(self):
        en_US_tmpl = "release-mozilla-beta_firefox_{}_complete_en-US_beetmover_candidates"
        en_US_partials_tmpl = "release-mozilla-beta_firefox_{}_partial_en-US_{}build{}_beetmover_candidates"
        l10n_tmpl = "release-mozilla-beta_firefox_{}_l10n_repack_beetmover_candidates_1"
        l10n_partials_tmpl = "release-mozilla-beta_firefox_{}_l10n_repack_partial_{}build{}_beetmover_candidates_1"
        requires = []
        for completes in (en_US_tmpl, l10n_tmpl):
            requires.extend([
                get_task_by_name(self.graph, completes.format(p))["taskId"]
                for p in ("macosx64", "win32")
            ])
        for partials in (en_US_partials_tmpl, l10n_partials_tmpl):
            requires.extend([
                get_task_by_name(self.graph, partials.format(platform, p_version, p_build_num))["taskId"]
                for platform in ("macosx64", "win32")
                for p_version, p_build_num in (('38.0', '1'), ('37.0', '2'))
            ])
        requires.append(get_task_by_name(self.graph, "release-mozilla-beta-firefox_chcksms")["taskId"])
        self.assertEqual(sorted(self.human_task["requires"]), sorted(requires))


class TestPushToMirrorsAutomatic(unittest.TestCase):
    maxDiff = 30000
    graph = None
    # we will end up with one task for each platform
    tasks = None
    human_task_name = "release-{}_{}_push_to_releases_human_decision".format("mozilla-beta",
                                                                             "firefox")

    TASK_SCHEMA = Schema({
        'task': {
            'provisionerId': 'aws-provisioner-v1',
            'workerType': 'opt-linux64',
        }
    }, extra=True, required=True)

    def setUp(self):
        test_kwargs = create_firefox_test_args({
            'checksums_enabled': True,
            'updates_enabled': True,
            'push_to_candidates_enabled': True,
            'push_to_releases_enabled': True,
            'push_to_releases_automatic': True,
            'branch': 'mozilla-beta',
            'repo_path': 'releases/mozilla-beta',
            'signing_pvt_key': PVT_KEY_FILE,
            'release_channels': ['beta', 'release'],
            'final_verify_channels': ['beta', 'release'],
            'partner_repacks_platforms': ['win32', 'macosx64'],
            'en_US_config': EN_US_CONFIG,
            'l10n_config': L10N_CONFIG,
        })
        self.graph = make_task_graph(**test_kwargs)
        self.task = get_task_by_name(
            self.graph, "release-{}_{}_push_to_releases".format("mozilla-beta", "firefox")
        )

    def test_common_assertions(self):
        do_common_assertions(self.graph)

    def test_task_schema(self):
        assert validate_with_humanized_errors(self.task, TestPushToMirrorsAutomatic.TASK_SCHEMA)

    def test_scopes_present(self):
        self.assertFalse("scopes" in self.task["task"])

    def test_graph_scopes(self):
        expected_graph_scopes = set([
            "queue:task-priority:high",
            "queue:define-task:aws-provisioner-v1/opt-linux64",
            "queue:create-task:aws-provisioner-v1/opt-linux64"
        ])
        self.assertTrue(expected_graph_scopes.issubset(self.graph["scopes"]))

    def test_version_in_command(self):
        command = self.task['task']['payload']['command']
        self.assertTrue("--version 42.0b2" in "".join(command))

    def test_build_num_in_command(self):
        command = self.task['task']['payload']['command']
        self.assertTrue("--build-number 3" in "".join(command))

    def test_exclude_in_command(self):
        command = self.task['task']['payload']['command']
        assert "--exclude '.*-EME-free/.*'" in "".join(command)

    def test_exclude_sha1_in_command(self):
        command = self.task['task']['payload']['command']
        assert "--exclude '.*/win32-sha1/.*'" in "".join(command)

    def test_human_decision_is_none(self):
        self.assertIsNone(get_task_by_name(self.graph, self.human_task_name))

    def test_requires(self):
        en_US_tmpl = "release-mozilla-beta_firefox_{}_complete_en-US_beetmover_candidates"
        en_US_partials_tmpl = "release-mozilla-beta_firefox_{}_partial_en-US_{}build{}_beetmover_candidates"
        l10n_tmpl = "release-mozilla-beta_firefox_{}_l10n_repack_beetmover_candidates_1"
        l10n_partials_tmpl = "release-mozilla-beta_firefox_{}_l10n_repack_partial_{}build{}_beetmover_candidates_1"
        requires = []
        for completes in (en_US_tmpl, l10n_tmpl):
            requires.extend([
                get_task_by_name(self.graph, completes.format(p))["taskId"]
                for p in ("macosx64", "win32")
            ])
        for partials in (en_US_partials_tmpl, l10n_partials_tmpl):
            requires.extend([
                get_task_by_name(self.graph, partials.format(platform, p_version, p_build_num))["taskId"]
                for platform in ("macosx64", "win32")
                for p_version, p_build_num in (('38.0', '1'), ('37.0', '2'))
            ])
        requires.append(get_task_by_name(self.graph, "release-mozilla-beta-firefox_chcksms")["taskId"])
        self.assertEqual(sorted(self.task["requires"]), sorted(requires))


class TestPushToMirrorsGraph2(unittest.TestCase):
    maxDiff = 30000
    graph = None
    # we will end up with one task for each platform
    tasks = None
    human_task_name = "release-{}_{}_push_to_releases_human_decision".format("mozilla-beta",
                                                                             "firefox")

    def setUp(self):
        test_kwargs = create_firefox_test_args({
            'checksums_enabled': True,
            'updates_enabled': True,
            'push_to_candidates_enabled': True,
            'push_to_releases_enabled': True,
            'push_to_releases_automatic': True,
            'branch': 'mozilla-beta',
            'repo_path': 'releases/mozilla-beta',
            'signing_pvt_key': PVT_KEY_FILE,
            'release_channels': ['beta', 'release'],
            'final_verify_channels': ['beta', 'release'],
            'partner_repacks_platforms': [],
            'en_US_config': EN_US_CONFIG,
            'l10n_config': L10N_CONFIG,
        })
        self.graph = make_task_graph(**test_kwargs)

        self.task = get_task_by_name(
            self.graph, "release-{}_{}_push_to_releases".format("mozilla-beta", "firefox")
        )

    def test_exclude_not_in_command(self):
        command = self.task['task']['payload']['command']
        assert "--exclude '.*-EME-free/.*'" not in "".join(command)

    def test_exclude_sha1_not_in_command(self):
        command = self.task['task']['payload']['command']
        assert "--exclude '.*/win32-sha1/.*'" not in "".join(command)
