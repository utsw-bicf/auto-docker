import pytest
from io import StringIO
import os

test_output_path = os.path.dirname(os.path.abspath(__file__)) + '/../'


@pytest.mark.dockerfiles
def test_dockerfiles():
    assert os.path.exists(os.path.join(
        test_output_path, "bicfbase/1.0.0/Dockerfile"))
