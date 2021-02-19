#!/usr/bin/env python3

import sys
import os
import pytest
from io import StringIO
sys.path.append(os.path.abspath('scripts/'))
import functions

test_output_path = os.path.dirname(os.path.abspath(__file__)) + '/../'

test_vars = []


@pytest.mark.test_check_org
def test_check_org():
    test_vars.append(functions.check_org())
    assert test_vars[0] == "bicf"


@pytest.mark.test_get_deploy_branch
def test_get_deploy_branch():
    test_vars.append(functions.get_deploy_branch())
    assert test_vars[1] == 'develop'


@pytest.mark.test_get_compare_range
def test_get_compare_range():
    test_vars.append(functions.get_compare_range())
    assert test_vars[2] == 'origin/develop HEAD'


@pytest.mark.test_changed_paths_in_range
def test_changed_paths_in_range():
    test_vars.append(functions.changed_paths_in_range(test_vars[2]))
    assert test_vars[3] == ['.github/workflows/workflow-ci.yml', '.gitignore', 'relations.yaml', 'scripts/check_pre_exist.py', 'scripts/functions.py', 'test_base/1.0.0/Dockerfile', 'test_base/1.0.0/unittest.yml', 'tests/test_functions.py']


@pytest.mark.test_print_changed
def test_print_changed(capfd):
    functions.print_changed(test_vars[2])
    test_out, test_err = capfd.readouterr()
    print(test_err)
    assert test_out == "Changed files between origin/develop HEAD:\n.github/workflows/workflow-ci.yml\n.gitignore\nrelations.yaml\nscripts/check_pre_exist.py\nscripts/functions.py\ntest_base/1.0.0/Dockerfile\ntest_base/1.0.0/unittest.yml\ntests/test_functions.py\n"


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


@pytest.mark.test_ensure_local_image
def test_ensure_local_image(capfd):
    functions.ensure_local_image(test_vars[0], 'base', '1.0.0')
    test_out, test_err = capfd.readouterr()
    print(test_out)
    assert "Image \'bicf/base:1.0.0\' already exists locally!" in test_err


@pytest.mark.test_build_image
def test_build_image(capfd):
    temp_var = functions.build_image(test_vars[0], test_vars[3])
    test_out, test_err = capfd.readouterr()
    print(test_out)
    assert "Dockerfile found: test_base/1.0.0/Dockerfile\nBuilding changed Dockerfiles...\n\nBuilding bicf/test_base:1.0.0...\nSuccessfully built bicf/test_base:1.0.0...\n" in test_err
    assert temp_var == True
    run_command = "docker image ls | grep 'bicf/test_base' | grep '1.0.0' | wc -l"
    os.system(run_command)
    test_out, test_err = capfd.readouterr()
    assert "\n1" in test_out


@pytest.mark.test_push_images
def test_push_images(capfd):
    functions.push_images(test_vars[0], test_vars[3])
    test_out, test_err = capfd.readouterr()
    print(test_out)
    assert "Dockerfile found: test_base/1.0.0/Dockerfile\nTest image found: 'bicf/test_base:1.0.0'\n            Skipping push of test image\n" in test_err


@pytest.mark.test_check_dockerfile_count
def test_check_dockerfile_count(capfd):
    test_vars.append(functions.check_dockerfile_count(test_vars[3]))
    test_out, test_err = capfd.readouterr()
    assert "Dockerfile found: test_base/1.0.0/Dockerfile" in test_err
    assert test_vars[4] == "test_base/1.0.0/Dockerfile"


@pytest.mark.test_check_test_image
def test_check_test_image():
    temp_var = functions.check_test_image(test_vars[3])
    assert temp_var == True
