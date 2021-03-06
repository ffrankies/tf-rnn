"""Test for the confusion_matrix module.

@since 0.6.1
"""
import pytest
import logging
import numpy as np

from tf_rnn.layers.utils.confusion_matrix import ConfusionMatrix, PerformanceMetrics

from ...test_data import PAD

MAX_LENGTH = 8

COMBINED_SCRAMBLED_BATCHES_4 = [
    [0, 1, 2, 3, 4, 5, 6, 7],
    [0, 1, 2, PAD, PAD, PAD, PAD, PAD],
    [0, 1, PAD, PAD, PAD, PAD, PAD, PAD],
    [0, 1, 2, 3, 4, PAD, PAD, PAD],
    [0, 1, 2, 3, PAD, PAD, PAD, PAD],
    [0, PAD, PAD, PAD, PAD, PAD, PAD, PAD],
    [0, 1, 2, 3, 4, 5, 6, PAD],
    [0, 1, 2, 3, 4, 5, PAD, PAD]
]

SIZES_COMBINED_SCRAMBLED_BATCHES_4 = [8, 3, 2, 5, 4, 1, 7, 6]

PREDICTIONS = COMBINED_SCRAMBLED_BATCHES_4

LABELS = [
    [0, 1, 2, 3, 5, 5, 1, 7],
    [0, 1, 2, PAD, PAD, PAD, PAD, PAD],
    [0, 1, PAD, PAD, PAD, PAD, PAD, PAD],
    [0, 1, 2, 3, 5, PAD, PAD, PAD],
    [1, 2, 3, 4, PAD, PAD, PAD, PAD],
    [1, PAD, PAD, PAD, PAD, PAD, PAD, PAD],
    [1, 2, 3, 4, 5, 5, 6, PAD],
    [1, 2, 3, 4, 5, 5, PAD, PAD]
]

SIZES = SIZES_COMBINED_SCRAMBLED_BATCHES_4

EXPECTED_MATRIX = [
    [4, 0, 0, 0, 0, 0, 0, 0],
    [4, 4, 0, 0, 0, 0, 1, 0],
    [0, 3, 3, 0, 0, 0, 0, 0],
    [0, 0, 3, 2, 0, 0, 0, 0],
    [0, 0, 0, 3, 0, 0, 0, 0],
    [0, 0, 0, 0, 4, 3, 0, 0],
    [0, 0, 0, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 1]
]

EXPECTED_METRICS = PerformanceMetrics(0.5, 3007/5040, 313/560, 0.5771628483)


class TestInsertPredictionIntoConfusionMatrix():
    def test_should_correctly_add_new_prediction(self):
        cm = ConfusionMatrix()
        cm.insert_prediction(0, 1)
        assert 1 in cm.row_labels
        assert 0 in cm.col_labels
        assert len(cm.matrix.keys()) == 1
        assert len(cm.matrix[1].keys()) == 1
        assert cm.matrix[1][0] == 1

    def test_should_correctly_update_old_prediction(self):
        cm = ConfusionMatrix()
        cm.insert_prediction(0, 1)
        cm.insert_prediction(0, 1)
        assert 1 in cm.row_labels
        assert 0 in cm.col_labels
        assert len(cm.matrix.keys()) == 1
        assert len(cm.matrix[1].keys()) == 1
        assert cm.matrix[1][0] == 2
        
class TestUpdateConfusionMatrix():
    def test_should_do_nothing_if_data_is_empty(self):
        predictions = []
        labels = []
        sizes = []
        cm = ConfusionMatrix()
        cm.update(predictions, labels, sizes)
        assert len(cm.matrix.keys()) == 0

    def test_should_correctly_update_with_batch_data(self):
        cm = ConfusionMatrix()
        cm.update(PREDICTIONS, LABELS, SIZES)
        assert cm.row_labels == cm.col_labels
        assert PAD not in cm.row_labels and PAD not in cm.col_labels
        assert list(cm.matrix[0].keys()) == [0]
        assert list(cm.matrix[1].keys())== [0, 1, 6]
        assert list(cm.matrix[2].keys())== [1, 2]
        assert list(cm.matrix[3].keys())== [2, 3]
        assert list(cm.matrix[4].keys())== [3]
        assert list(cm.matrix[5].keys())== [4, 5]
        assert list(cm.matrix[6].keys())== [6]
        assert list(cm.matrix[7].keys())== [7]
        assert cm.matrix[0][0] == 4
        assert cm.matrix[1][0] == 4 and cm.matrix[1][1] == 4 and cm.matrix[1][6] == 1
        assert cm.matrix[2][1] == 3 and cm.matrix[2][2] == 3
        assert cm.matrix[3][2] == 3 and cm.matrix[3][3] == 2
        assert cm.matrix[4][3] == 3
        assert cm.matrix[5][4] == 4 and cm.matrix[5][5] == 3
        assert cm.matrix[6][6] == 1
        assert cm.matrix[7][7] == 1

class TestConfusionMatrixToArray():
    def test_should_return_empty_array_when_matrix_is_empty(self):
        cm = ConfusionMatrix()
        matrix = cm.to_array()
        assert matrix == []

    def test_should_correctly_convert_matrix_with_data_to_array(self):
        cm = ConfusionMatrix()
        cm.update(PREDICTIONS, LABELS, SIZES)
        matrix = cm.to_array()
        assert matrix == EXPECTED_MATRIX
        assert cm.matrix[0][0] == 4
        assert cm.matrix[1][0] == 4 and cm.matrix[1][1] == 4 and cm.matrix[1][6] == 1
        assert cm.matrix[2][1] == 3 and cm.matrix[2][2] == 3
        assert cm.matrix[3][2] == 3 and cm.matrix[3][3] == 2
        assert cm.matrix[4][3] == 3
        assert cm.matrix[5][4] == 4 and cm.matrix[5][5] == 3
        assert cm.matrix[6][6] == 1
        assert cm.matrix[7][7] == 1

class TestPerformanceMetrics():

    def setup_method(self):
        self.cm = ConfusionMatrix()
        self.cm.update(PREDICTIONS, LABELS, SIZES)
        
    def test_does_not_crash_if_matrix_empty(self):
        cm = ConfusionMatrix()
        try:
            cm.performance_metrics()
        except Exception:
            pytest.fail()

    def test_does_not_crash(self):
        try:
            self.cm.performance_metrics()
        except Exception:
            pytest.fail()
    
    def test_correctly_calculates_accuracy(self):
        assert self.cm.performance_metrics().accuracy == EXPECTED_METRICS.accuracy

    def test_correctly_calculates_precision(self):
        assert self.cm.performance_metrics().precision == EXPECTED_METRICS.precision

    def test_correctly_calculates_recall(self):
        assert self.cm.performance_metrics().recall == EXPECTED_METRICS.recall

    def test_correctly_calculates_f1_score(self):
        assert np.allclose([self.cm.performance_metrics().f1_score], [EXPECTED_METRICS.f1_score])
