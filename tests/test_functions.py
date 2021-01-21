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
    assert test_vars[3] == ['.github/workflows/workflow-ci.yml', '.gitignore', 'base/1.0.1/Dockerfile',
                            'base/1.0.1/unittest.yml', 'relations.yaml', 'scripts/functions.py', 'tests/test_functions.py']


@pytest.mark.test_print_changed
def test_print_changed(capfd):
    functions.print_changed(test_vars[2], test_vars[3])
    test_out, test_err = capfd.readouterr()
    print(test_err)
    assert test_out == "Changed files between origin/develop HEAD:\n.github/workflows/workflow-ci.yml\n.gitignore\nbase/1.0.1/Dockerfile\nbase/1.0.1/unittest.yml\nrelations.yaml\nscripts/functions.py\ntests/test_functions.py\n"


@pytest.mark.test_build_docker_cmd
def build_docker_cmd(capfd):
    test_output = []
    for command in ['build', 'images', 'pull', 'push', 'tag']:
        functions.build_docker_cmd(
            command, test_vars[0], 'base', '1.0.1', '1.0.0')
        test_out, test_err = capfd.readouterr()
        test_output.append(test_out)
        print(test_err)
    assert test_output == ['docker build -f "base/1.0.1/Dockerfile" -t "bicf/base:1.0.1" "base/1.0.1/"', 'docker images bicf/base:1.0.1 -q',
                           'docker pull bicf/base:1.0.1', 'docker push bicf/base:1.0.1', 'docker tag bicf/base:1.0.0 bicf/base:1.0.1']

@pytest.mark.test_build_images
def test_build_images(capfd):
    functions.build_images(test_vars[0], test_vars[3])
    test_out, test_err = capfd.readouterr()
    print(test_err)
    assert test_out == "Building changed Dockerfiles...\n\nBuilding bicf/base:1.0.1...\nsha256:451fd06cd4d9c27c35005098ec83b1fd7adf9acf3df905fa5015bec56b4474d3\nSuccessfully built bicf/base:1.0.1...\nNo currently set 'latest' image, creating link and tagging as 'latest'.\n"
    run_command = "docker image ls | grep 'bicf/base' | grep \"1.0.1\\|latest\" | wc -l"
    os.system(run_command)
    test_out, test_err = capfd.readouterr()
    assert test_out == "\n2\n"
