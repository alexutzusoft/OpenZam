import os

def get_username():
    """
    Gets the username from the environment variables.
    """
    return os.getlogin()
