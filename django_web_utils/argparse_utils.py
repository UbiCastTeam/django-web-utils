import argparse


def insert_argument_at_index(parser: argparse.ArgumentParser, index: int, *args, **kwargs) -> None:
    """
    Insert an argument at the specified index in the parser.
    This is useful to control the order of arguments in the help output.
    The argparse module do not allow inserting arguments at a specific index natively.
    """
    parser.add_argument(*args, **kwargs)

    # Change order in "_actions" (impacts "usage:" of command help)
    action = parser._actions.pop(-1)
    parser._actions.insert(index, action)

    # Change order in "_action_groups" (impacts "options:" of command help)
    for group in parser._action_groups:
        if action in group._group_actions:
            group._group_actions.remove(action)
            group._group_actions.insert(index, action)
            break
