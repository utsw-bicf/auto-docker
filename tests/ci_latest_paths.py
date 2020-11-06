#!/usr/bin/env python3
"""
Prints out the paths for the unittest.yml files for all latest images to run their pytests
"""

import os
import sys
import re
import yaml


def load_yaml(master_yaml):
    """
    Loads a yaml file and returns a python yaml object
    :param yaml_file: the yaml file to open and read
    """
    with open(master_yaml) as yaml_file:
        yaml_data = yaml.safe_load(yaml_file)
    yaml_file.close()
    return yaml_data


def pull_image(docker_image):
    """
    Ensures that the version of the image specified has been pulled
    :param docker_image: str: Docker image to pull in the format '<organization>/<image_name>:<version>'
    """
    if os.system("docker pull " + docker_image) != 0:
        print("ERROR: Unable to build " + docker_image)
        sys.exit(1)


def main():
    """
    Main method

    """
    if len(sys.argv) < 1:
        print(
            "Usage python3 scripts/getLatestPaths.py <docker_owner> <relations.yaml path>")
        sys.exit(1)
    else:
        owner = sys.argv[1]
        relations = load_yaml(os.path.abspath(sys.argv[2]))
        latest_images = relations['latest']
        for image in latest_images:
            tag = latest_images[image]
            image_name = "{}/{}:{}".format(owner, image, tag).replace("+", "_")
            pull_image(image_name)
            image_path = image + "/" + tag + "/unittest.yml"
            if os.system("python3 tests/imagecheck.py \"" + owner + "\" " + image_path) != 0:
                print("ERROR: Image testing failed for " + image_name)
                sys.exit(1)


if __name__ == "__main__":
    main()
