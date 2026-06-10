import argparse

import pytest

from django_web_utils.argparse_utils import insert_argument_at_index


@pytest.fixture
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument('--foo')
    p.add_argument('--bar')
    return p


def test_insert_at_index_changes_actions_order(parser):
    insert_argument_at_index(parser, 1, '--baz')
    action_names = [a.dest for a in parser._actions]
    # --baz should be at index 1, before --foo and --bar (index 0 is --help)
    assert action_names.index('baz') == 1
    assert action_names.index('foo') > 1
    assert action_names.index('bar') > 1


def test_insert_at_index_changes_group_actions_order(parser):
    insert_argument_at_index(parser, 1, '--baz')
    options_group = next(g for g in parser._action_groups if g.title in ('options', 'optional arguments'))
    group_action_names = [a.dest for a in options_group._group_actions]
    assert group_action_names.index('baz') == 1
    assert group_action_names.index('foo') > 1
    assert group_action_names.index('bar') > 1


def test_insert_kwargs_are_forwarded():
    parser = argparse.ArgumentParser()
    insert_argument_at_index(parser, 1, '--count', type=int, default=5, help='a count')
    action = next(a for a in parser._actions if a.dest == 'count')
    assert action.type is int
    assert action.default == 5
