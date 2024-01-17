import pytest
import os
from PyQt5.QtWidgets import QApplication
from snub.gui.main import MainWindow

# @pytest.fixture(scope="module")
# def qt_app():
#     """Fixture to create a QApplication instance for the tests."""
#     if QApplication.instance() is None:
#         app = QApplication([])
#     else:
#         app = QApplication.instance()
#     yield app


@pytest.fixture(scope="module")
def project_directory():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "project")


@pytest.fixture(scope="module")
def qt_app():
    """Fixture to create a QApplication instance for the tests."""
    app = QApplication([])
    yield app


@pytest.fixture
def main_window(qt_app, project_directory):
    """Fixture to create MainWindow instance."""
    window = MainWindow([project_directory])
    return window


def test_main_window_loads(qt_app, main_window):
    """Test to check if the main window loads without error."""
    main_window.show()
    assert main_window.isVisible()
