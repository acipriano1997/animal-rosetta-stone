import pandas as pd
from ars_receiver_harness.pr0006 import _binary_outcome

def test_rdc005_positive_class_is_approach():
    labels = pd.Series(['approach', 'avoidance', 'approach'])
    actual = _binary_outcome(labels).tolist()
    assert actual == [1, 0, 1]

def test_unrecognized_receiver_label_rejected():
    labels = pd.Series(['approach', 'unobserved'])
    try:
        _binary_outcome(labels)
    except ValueError:
        return
    raise AssertionError('Unexpected outcome label was admitted')
