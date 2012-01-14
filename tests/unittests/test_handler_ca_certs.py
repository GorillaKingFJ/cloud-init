from unittest import TestCase
from mocker import MockerTestCase

from cloudinit.CloudConfig.cc_ca_certs import handle, write_file, update_ca_certs, add_ca_certs, remove_default_ca_certs


class TestNoConfig(MockerTestCase):
    def setUp(self):
        super(TestNoConfig, self).setUp()
        self.name = "ca-certs"
        self.cloud_init = None
        self.log = None
        self.args = []

    def test_no_config(self):
        """
        Test that nothing is done if no ca-certs configuration is provided.
        """
        config = {"unknown-key": "value"}

        self.mocker.replace(write_file, passthrough=False)
        self.mocker.replace(update_ca_certs, passthrough=False)
        self.mocker.replay()

        handle(self.name, config, self.cloud_init, self.log, self.args)


class TestConfig(MockerTestCase):
    def setUp(self):
        super(TestConfig, self).setUp()
        self.name = "ca-certs"
        self.cloud_init = None
        self.log = None
        self.args = []

        # Mock out the functions that actually modify the system
        self.mock_add = self.mocker.replace(add_ca_certs, passthrough=False)
        self.mock_update = self.mocker.replace(update_ca_certs, passthrough=False)
        self.mock_remove = self.mocker.replace(remove_default_ca_certs, passthrough=False)
        # Order must be correct
        self.mocker.order()

    def test_no_trusted_list(self):
        """
        Test that no certificates are written if the 'trusted' key is not
        present.
        """
        config = {"ca-certs": {}}

        # No functions should be called
        self.mock_update()
        self.mocker.replay()

        handle(self.name, config, self.cloud_init, self.log, self.args)

    def test_empty_trusted_list(self):
        """Test that no certificate are written if 'trusted' list is empty"""
        config = {"ca-certs": {"trusted": []}}

        # No functions should be called
        self.mock_update()
        self.mocker.replay()

        handle(self.name, config, self.cloud_init, self.log, self.args)

    def test_single_trusted(self):
        """Test that a single cert gets passed to add_ca_certs"""
        config = {"ca-certs": {"trusted": ["CERT1"]}}

        self.mock_add(["CERT1"])
        self.mock_update()
        self.mocker.replay()

        handle(self.name, config, self.cloud_init, self.log, self.args)

    def test_multiple_trusted(self):
        """Test that multiple certs get passed to add_ca_certs"""
        config = {"ca-certs": {"trusted": ["CERT1", "CERT2"]}}

        self.mock_add(["CERT1", "CERT2"])
        self.mock_update()
        self.mocker.replay()

        handle(self.name, config, self.cloud_init, self.log, self.args)

    def test_remove_default_ca_certs(self):
        """Test remove_defaults works as expected"""
        config = {"ca-certs": {"remove-defaults": True}}

        self.mock_remove()
        self.mock_update()
        self.mocker.replay()

        handle(self.name, config, self.cloud_init, self.log, self.args)

    def test_no_remove_defaults_if_false(self):
        """Test remove_defaults is not called when config value is False"""
        config = {"ca-certs": {"remove-defaults": False}}

        self.mock_update()
        self.mocker.replay()

        handle(self.name, config, self.cloud_init, self.log, self.args)

    def test_correct_order_for_remove_then_add(self):
        """Test remove_defaults is not called when config value is False"""
        config = {"ca-certs": {"remove-defaults": True, "trusted": ["CERT1"]}}

        self.mock_remove()
        self.mock_add(["CERT1"])
        self.mock_update()
        self.mocker.replay()

        handle(self.name, config, self.cloud_init, self.log, self.args)


class TestAddCaCerts(MockerTestCase):
    def test_no_certs_in_list(self):
        """Test that no certificate are written if not provided."""
        mock = self.mocker.replace(write_file, passthrough=False)
        self.mocker.replay()

        add_ca_certs([])

    def test_single_cert(self):
        """Test adding a single certificate to the trusted CAs"""
        cert = "CERT1\nLINE2\nLINE3"

        mock = self.mocker.replace(write_file, passthrough=False)
        mock("/usr/share/ca-certificates/cloud-init-provided.crt",
             cert, "root", "root", "644")
        self.mocker.replay()

        add_ca_certs([cert])

    def test_multiple_certs(self):
        """Test adding multiple certificate to the trusted CAs"""
        certs = ["CERT1\nLINE2\nLINE3", "CERT2\nLINE2\nLINE3"]
        expected_cert_file = "\n".join(certs)

        mock = self.mocker.replace(write_file, passthrough=False)
        mock("/usr/share/ca-certificates/cloud-init-provided.crt",
             expected_cert_file, "root", "root", "644")
        self.mocker.replay()

        add_ca_certs(certs)


class TestUpdateCaCerts(MockerTestCase):
    def test_commands(self):
        mock_check_call = self.mocker.replace("subprocess.check_call",
                                              passthrough=False)
        mock_check_call(["dpkg-reconfigure", "ca-certificates"])
        mock_check_call(["update-ca-certificates"])
        self.mocker.replay()

        update_ca_certs()


#class TestRemoveDefaultCaCerts(MockerTestCase):
#    def test_commands(self):
#        mock_check_call = self.mocker.replace("subprocess.check_call",
#                                              passthrough=False)
#        mock_check_call(["dpkg-reconfigure", "ca-certificates"])
#        mock_check_call(["update-ca-certificates"])
#        self.mocker.replay()
#
#        update_ca_certs()
