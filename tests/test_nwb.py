import os
import shutil
import pytest

from snub.io import create_project_from_nwb
from dandi.download import download


@pytest.fixture(scope="module")
def setup_and_teardown():
    """Download NWB file and then delete it and the SNUB project after the test."""

    # Create temporary directory for NWB file and SNUB plot
    tmp_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "tmp_nwb")
    os.makedirs(tmp_dir, exist_ok=True)

    # Download NWB file
    nwb_url = "https://api.dandiarchive.org/api/dandisets/000251/versions/draft/assets/b28fcb84-2e23-472c-913c-383151bc58ef/download/"
    download(nwb_url, tmp_dir)

    # Yield path to NWB file
    nwb_file = os.path.join(tmp_dir, "sub-108_ses-Ca-VS-VR-2.nwb")
    yield nwb_file

    # Delete temporary directory
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_nwb_conversion(setup_and_teardown):
    """Test snub.io.nwb.create_project_from_nwb"""
    nwb_file = setup_and_teardown
    name = os.path.splitext(os.path.basename(nwb_file))[0]
    project_directory = os.path.join(os.path.dirname(nwb_file), f"SNUB-{name}")
    create_project_from_nwb(project_directory, nwb_file)
