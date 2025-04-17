# tests/test_db_utils.py
import unittest
import json
import os
import sys
from unittest.mock import patch, mock_open, MagicMock

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

# Now import the modules from src
# Need to ensure db_utils can be imported
# If db_utils uses other src modules, ensure they are importable too
try:
    from db_utils import load_data, save_data
except ImportError as e:
    print(f"Error importing db_utils: {e}")
    # Handle the error or skip tests if necessary
    # For now, let's define dummy functions if import fails
    # This allows the test file to be parsed, but tests will likely fail
    # A better approach is to fix the import path issues
    def load_data(filepath, default=None): return default
    def save_data(filepath, data): pass


class TestDbUtils(unittest.TestCase):
    """
    Test cases for the db_utils module functions.
    Uses mocking to avoid actual file system operations.
    """

    def test_load_data_success(self):
        """
        Test loading data from a file that exists and contains valid JSON.
        """
        mock_data = {"key": "value", "number": 123}
        mock_json_data = json.dumps(mock_data)
        # Mock os.path.exists to return True
        # Mock open to return the mock JSON data
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=mock_json_data)) as mocked_file:
            loaded_data = load_data('dummy/path/data.json')
            mocked_file.assert_called_once_with('dummy/path/data.json', 'r', encoding='utf-8')
            self.assertEqual(loaded_data, mock_data)

    def test_load_data_file_not_found(self):
        """
        Test loading data when the file does not exist.
        It should return the default value (an empty dictionary).
        """
        default_value = {}
        # Mock os.path.exists to return False
        with patch('os.path.exists', return_value=False):
            loaded_data = load_data('dummy/path/nonexistent.json', default=default_value)
            self.assertEqual(loaded_data, default_value)
            # Ensure open was not called
            # We need a way to assert open was not called, patching open itself might be complex here
            # Alternatively, assert the default value is returned directly

    def test_load_data_file_not_found_default_list(self):
        """
        Test loading data when the file does not exist with a list default.
        """
        default_value = []
        with patch('os.path.exists', return_value=False):
            loaded_data = load_data('dummy/path/nonexistent.json', default=default_value)
            self.assertEqual(loaded_data, default_value)


    def test_load_data_empty_file(self):
        """
        Test loading data from an empty file.
        It should raise a json.JSONDecodeError or return the default.
        The current implementation might raise JSONDecodeError. Let's test that.
        """
        default_value = {"default": True}
        # Mock os.path.exists to return True
        # Mock open to return empty data
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='')) as mocked_file:
             # Depending on implementation, it might return default or raise error
             # Let's assume it should return default on decode error
             # Update: The original db_utils catches JSONDecodeError and returns default
             loaded_data = load_data('dummy/path/empty.json', default=default_value)
             self.assertEqual(loaded_data, default_value)
             mocked_file.assert_called_once_with('dummy/path/empty.json', 'r', encoding='utf-8')


    def test_load_data_invalid_json(self):
        """
        Test loading data from a file with invalid JSON.
        It should catch the JSONDecodeError and return the default value.
        """
        default_value = {"error": "invalid json"}
        # Mock os.path.exists to return True
        # Mock open to return invalid JSON data
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='{invalid json')) as mocked_file:
            loaded_data = load_data('dummy/path/invalid.json', default=default_value)
            self.assertEqual(loaded_data, default_value)
            mocked_file.assert_called_once_with('dummy/path/invalid.json', 'r', encoding='utf-8')


    def test_save_data_success(self):
        """
        Test saving data to a file successfully.
        """
        data_to_save = {"name": "test", "items": [1, 2, 3]}
        expected_json_output = json.dumps(data_to_save, indent=4)
        # Mock open and the write method
        m = mock_open()
        with patch('builtins.open', m) as mocked_file, \
             patch('os.makedirs') as mock_makedirs, \
             patch('os.path.dirname', return_value='dummy/path') as mock_dirname: # Mock dirname

            save_data('dummy/path/output.json', data_to_save)

            # Assert that dirname was called
            mock_dirname.assert_called_once_with('dummy/path/output.json')
            # Assert that makedirs was called with the correct path and exist_ok=True
            mock_makedirs.assert_called_once_with('dummy/path', exist_ok=True)
            # Assert that open was called correctly
            mocked_file.assert_called_once_with('dummy/path/output.json', 'w', encoding='utf-8')
            # Assert that write was called with the correct JSON data
            handle = m() # Get the file handle mock
            handle.write.assert_called_once_with(expected_json_output)

    def test_save_data_io_error(self):
        """
        Test saving data when an IOError occurs during file writing.
        It should catch the error and potentially log it (though we can't easily test logging here).
        The function should not crash.
        """
        data_to_save = {"error": "test"}
        # Mock open to raise an IOError on write
        m = mock_open()
        m().write.side_effect = IOError("Disk full")

        with patch('builtins.open', m) as mocked_file, \
             patch('os.makedirs'), \
             patch('os.path.dirname', return_value='dummy/path'):
            # We expect the function to execute without raising the IOError further
            try:
                save_data('dummy/path/error.json', data_to_save)
            except IOError:
                self.fail("save_data() raised IOError unexpectedly!")

            # Assert that open was called
            mocked_file.assert_called_once_with('dummy/path/error.json', 'w', encoding='utf-8')
            # Assert that write was called (even though it raised an error internally)
            handle = m()
            handle.write.assert_called_once() # Check it was called


if __name__ == '__main__':
    # Ensure the test runner can find the src modules
    print(f"System path: {sys.path}")
    print(f"Current working directory: {os.getcwd()}")
    # Run tests
    unittest.main()

