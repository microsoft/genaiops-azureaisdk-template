"""This is a sample test file to test the test framework."""


def test_print():
    """Test the sample test."""
    try:
        print("Hello") is None
    except TypeError as e:
        print(e)
        assert False
