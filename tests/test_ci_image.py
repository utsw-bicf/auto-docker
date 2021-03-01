#!/usr/bin/env python3


import sys
import os
import pytest
import yaml
from io import StringIO
sys.path.append(os.path.abspath("scripts/"))
import ci_images

test_vars = []

@pytest.mark.test_run_bash_cmd
def test_run_bash_cmd():
    test_out = ci_images.run_bash_cmd('ls -lorthap')
    assert test_out == ["bash", "-c", "ls -lorthap"]


@pytest.mark.test_get_test_list
def test_get_test_list():
    test_out = ci_images.get_test_list('tests/Test_Unittest.yml')
    assert test_out == [('parallel --version | head -n1', 'GNU parallel 20161222\n'), ('pandoc --version | head -n2', 'pandoc 1.19.2.4\nCompiled with pandoc-types 1.17.0.5, texmath 0.9.4.4, skylighting 0.3.3.1\n')]


@pytest.mark.test_run_tests
def test_run_tests():
    test_out = ci_image.run_tests('bicf/base:1.0.0', 'tests/Test_Unittest.yml')
    assert test_out == False