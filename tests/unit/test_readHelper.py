import os
import unittest
import yaml
from aws_lambda.helpers import read


class TestReadHelper(unittest.TestCase):

    TEST_FILE = 'readTmp.txt'

    def setUp(self):
        with open(TestReadHelper.TEST_FILE, 'w') as tmp_file:
            tmp_file.write('testYaml: testing')

    def tearDown(self):
        os.remove(TestReadHelper.TEST_FILE)

    def test_read_no_loader_non_binary(self):
        fileContents = read(TestReadHelper.TEST_FILE)
        self.assertEqual(fileContents, 'testYaml: testing')

    def test_read_yaml_loader_non_binary(self):
        testYaml = read(TestReadHelper.TEST_FILE, loader=yaml.full_load)
        self.assertEqual(testYaml['testYaml'], 'testing')

    def test_read_no_loader_binary_mode(self):
        fileContents = read(TestReadHelper.TEST_FILE, binary_file=True)
        self.assertEqual(fileContents, b'testYaml: testing')

    def test_read_yaml_loader_binary_mode(self):
        testYaml = read(
            TestReadHelper.TEST_FILE,
            loader=yaml.full_load,
            binary_file=True
        )
        self.assertEqual(testYaml['testYaml'], 'testing')
