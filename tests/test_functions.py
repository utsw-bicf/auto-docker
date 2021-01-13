#!/usr/bin/env python3
"""
Prints out the paths for the unittest.yml files for all latest images to run their pytests
"""

import os
import sys
import re
import yaml
import pytest


@pytest.mark.test_organization
def test_org():
    assert check_org() == "bicf"
