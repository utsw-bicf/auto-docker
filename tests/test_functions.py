#!/usr/bin/env python3

import sys
import os
import pytest
from io import StringIO
sys.path.append(os.path.abspath('scripts/'))
import functions

test_output_path = os.path.dirname(os.path.abspath(__file__)) + '/../'
if not 'DEPLOY_BRANCH' in os.environ:
    os.environ['DEPLOY_BRANCH'] = 'test_branch'
if not 'DOCKERHUB_ORG' in os.environ:
    os.environ['DOCKERHUB_ORG'] = 'test_org'
no_image = False
dockerfile_path = ''

test_vars = []


@pytest.mark.test_check_org
def test_check_org():
    test_vars.append(functions.check_org())
    assert test_vars[0] != ''


@pytest.mark.test_get_deploy_branch
def test_get_deploy_branch():
    test_vars.append(functions.get_deploy_branch())
    assert test_vars[1] != ''


@pytest.mark.test_get_compare_range
def test_get_compare_range():
    test_vars.append(functions.get_compare_range())
    assert test_vars[2] != ''


@pytest.mark.test_changed_paths_in_range
def test_changed_paths_in_range():
    global no_image
    global dockerfile_path    
    test_vars.append(functions.changed_paths_in_range(test_vars[2]))
    for changed_path in test_vars[3]:
        if '/dockerfile' in changed_path.lower():
            test_vars.append(str(changed_path))
            no_image = False
            break
        else:
            no_image = True
    if no_image == True:
        os.makedirs('testing_base_image/0.0.1')
        with open('testing_base_image/0.0.1/Dockerfile', 'w') as f:
            print("FROM ubuntu:18.04 \
                    ENV DEBIAN_FRONTEND=noninteractive \
                    RUN apt-get update -y --fix-missing && \\\
                    apt-get upgrade -y && \\\
                    apt-get dist-upgrade -y && \\\
                    apt-get autoremove -y && \\\
                    apt-get update -y --fix-missing && \\\
                    apt-get upgrade -y \
                    RUN locale \
                    RUN apt-get install -y gcc g++ apt-utils wget gzip pigz pbzip2 zip software-properties-common make parallel pandoc git \
                    RUN while parallel --citation; do echo \"will cite\"; done \
                    ENV LC_ALL=C.UTF-8 \
                    ENV LANG=C.UTF-8 \
                    VOLUME /var/tmp/results \
                    VOLUME /var/tmp/data)")
        test_vars[4] = 'testing_base_image/0.0.1/Dockerfile'
        assert no_image == True
    else:
        print(dockerfile_path)
        assert test_vars[3] != None


@pytest.mark.test_print_changed
def test_print_changed(capfd):
    if no_image == True:
        assert True
    else:
        functions.print_changed(test_vars[2])
        test_out, test_err = capfd.readouterr()
        print(test_err)
        assert test_out != None


@pytest.mark.test_build_docker_cmd
def build_docker_cmd(capfd):
    test_output = []
    for command in ['build', 'images', 'pull', 'push', 'tag']:
        functions.build_docker_cmd(
            command, test_vars[0], 'base', '1.0.1', '1.0.0')
        test_out, test_err = capfd.readouterr()
        test_output.append(test_out)
        print(test_err)
    assert test_output == ['docker build -f "base/1.0.1/Dockerfile" -t "testing_base/base:1.0.1" "base/1.0.1/"', 'docker images testing_base/base:1.0.1 -q',
                           'docker pull testing_base/base:1.0.1', 'docker push testing_base/base:1.0.1', 'docker tag testing_base/base:1.0.0 testing_base/base:1.0.1']


@pytest.mark.test_ensure_local_image
def test_ensure_local_image(capfd):
    global dockerfile_path
    print(dockerfile_path)
    tool_name = dockerfile_path.split('/')[0]
    tool_version = dockerfile_path.split('/')[1]
    functions.ensure_local_image(test_vars[0], tool_name, tool_version)
    test_out, test_err = capfd.readouterr()
    print(test_out)
    assert ("Image \'{}/{}:{}\' already exists locally!".format(test_vars[0], tool_name, tool_version) in test_err) or (
        "Image {}/{}:{} does not exist locally for tagging, building..." in test_out)


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
    temp_var = functions.check_test_image(test_vars[3][6])
    assert temp_var == True
