import importlib
import sys
import types
import unittest


def import_plugin_with_certbot_stubs():
    errors_module = types.ModuleType("certbot.errors")

    class PluginError(Exception):
        pass

    errors_module.PluginError = PluginError

    certbot_module = types.ModuleType("certbot")
    certbot_module.errors = errors_module

    plugins_module = types.ModuleType("certbot.plugins")
    dns_common_module = types.ModuleType("certbot.plugins.dns_common")

    class DNSAuthenticator:
        def __init__(self, *args, **kwargs):
            pass

    dns_common_module.DNSAuthenticator = DNSAuthenticator
    plugins_module.dns_common = dns_common_module

    sys.modules.setdefault("certbot", certbot_module)
    sys.modules.setdefault("certbot.errors", errors_module)
    sys.modules.setdefault("certbot.plugins", plugins_module)
    sys.modules.setdefault("certbot.plugins.dns_common", dns_common_module)

    return importlib.import_module(
        "certbot_dns_tencentcloud.certbot_tencentcloud_plugins"
    )


plugin = import_plugin_with_certbot_stubs()


class FakeTencentCloudClient:
    created_records = []
    deleted_records = []

    def __init__(self, secret_id, secret_key, debug=False):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.debug = debug

    def create_record(self, domain, sub_domain, record_type, value):
        record_id = len(self.created_records) + 100
        self.created_records.append(
            {
                "domain": domain,
                "sub_domain": sub_domain,
                "record_type": record_type,
                "value": value,
                "record_id": record_id,
            }
        )
        return {"RecordId": record_id}

    def delete_record(self, domain, record_id):
        self.deleted_records.append((domain, record_id))


class AuthenticatorCleanupTest(unittest.TestCase):
    def setUp(self):
        self.original_client = plugin.TencentCloudClient
        plugin.TencentCloudClient = FakeTencentCloudClient
        FakeTencentCloudClient.created_records = []
        FakeTencentCloudClient.deleted_records = []

    def tearDown(self):
        plugin.TencentCloudClient = self.original_client

    def make_authenticator(self):
        authenticator = plugin.Authenticator.__new__(plugin.Authenticator)
        authenticator.secret_id = "secret-id"
        authenticator.secret_key = "secret-key"
        authenticator.cleanup_maps = {}
        authenticator.conf = lambda option: False
        authenticator.determine_base_domain = lambda domain: ("example.com", [])
        return authenticator

    def test_cleanup_tracks_duplicate_validation_names_independently(self):
        authenticator = self.make_authenticator()
        validation_name = "_acme-challenge.example.com"

        authenticator._perform("example.com", validation_name, "first-validation")
        authenticator._perform("example.com", validation_name, "second-validation")

        self.assertEqual(
            [
                ("_acme-challenge", "first-validation", 100),
                ("_acme-challenge", "second-validation", 101),
            ],
            [
                (record["sub_domain"], record["value"], record["record_id"])
                for record in FakeTencentCloudClient.created_records
            ],
        )

        authenticator._cleanup("example.com", validation_name, "first-validation")
        authenticator._cleanup("example.com", validation_name, "second-validation")

        self.assertEqual(
            [("example.com", 100), ("example.com", 101)],
            FakeTencentCloudClient.deleted_records,
        )
        self.assertEqual({}, authenticator.cleanup_maps)


if __name__ == "__main__":
    unittest.main()
