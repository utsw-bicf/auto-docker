#!/usr/bin/env python3
import yaml
import re
import sys
import os
import pytest
from io import StringIO
sys.path.append(os.path.abspath('scripts/'))
import functions

test_output_path = os.path.dirname(os.path.abspath(__file__)) + '/../'

test_vars = []


@pytest.mark.test_organization
def test_org():
    test_vars.append(functions.check_org())
    assert test_vars[0] == "bicf"


@pytest.mark.test_deploy_branch
def test_deploy_branch():
    test_vars.append(functions.get_deploy_branch())
    assert test_vars[1] == 'develop'


@pytest.mark.test_compare_range
def test_compare_range():
    test_vars.append(functions.get_compare_range())
    assert test_vars[2] == 'origin/develop HEAD'

@pytest.mark.test_changed_paths_in_range
def test_changed_paths_in_range():
    test_vars.append(functions.changed_paths_in_range(test_vars[2]))
    assert test_vars[3] == ['.github/workflows/workflow-ci.yml', '.gitignore', 'base/1.0.1/Dockerfile', 'base/1.0.1/unittest.yml', 'relations.yaml', 'scripts/__pycache__/functions.cpython-37.pyc', 'scripts/functions.py', 'tests/test_functions.py']

@pytest.mark.test_print_changed
def test_print_changed(capfd):
    functions.print_changed(test_vars[2], test_vars[3])
    test_out, test_err = capfd.readouterr()
    print(test_err)
    assert test_out == "Changed files between origin/develop HEAD:\n.github/workflows/workflow-ci.yml\n.gitignore\nbase/1.0.1/Dockerfile\nbase/1.0.1/unittest.yml\nrelations.yaml\nscripts/__pycache__/functions.cpython-37.pyc\nscripts/functions.py\ntests/test_functions.py\n"

@pytest.mark.test_build_images
def test_build_images(capfd):
    functions.build_images(test_vars[0], test_vars[3])
    test_out, test_err = capfd.readouterr()
    print(test_err)
    assert test_out == ""