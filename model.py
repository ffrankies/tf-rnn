"""
An RNN model implementation in tensorflow.

Copyright (c) 2017 Frank Derry Wanye

Date: 22 October, 2017
"""

import numpy as np
import tensorflow as tf
import logging
import ray
import time

from . import constants
from . import setup
from . import dataset
from . import saver
from . import tensorboard
from . import settings

from .layers.input_layer import *
from .layers.hidden_layer import *
# from .layers.output_layer import *
from .layers.performance_layer import *

class RNNModel(object):
    """
    A basic RNN implementation in tensorflow.
    """

    def __init__(self):
        """
        Constructor for an RNN Model.
        """
        self.settings = settings.Settings()
        self.model_path = saver.create_model_dir(self.settings.general.model_name)
        self.logger = setup.setup_logger(self.settings.logging, self.model_path)
        self.logger.info("RNN settings: %s" % self.settings)
        self.dataset = dataset.Dataset(self.logger, self.settings.rnn.dataset, self.settings.train)
        self.create_graph()
    # End of __init__()

    def create_graph(self):
        """
        Creates all internal tensorflow operations and variables inside a local graph and session.
        """
        self.graph = tf.Graph()
        with self.graph.as_default():
            self.training()
            self.session = tf.Session(graph=self.graph)
            self.init_saver()
            self.session.run(tf.global_variables_initializer())
    # End of create_graph()

    def training(self):
        """
        Creates tensorflow variables and operations needed for training.
        """
        total_loss = self.performance_evaluation()
        with tf.variable_scope(constants.TRAINING):
            self.learning_rate = tf.Variable(
                initial_value=self.settings.train.learn_rate,
                dtype=tf.float32,
                name="learning_rate")
            self.train_step_fun = tf.train.AdagradOptimizer(self.learning_rate).minimize(total_loss)
    # End of training()

    def performance_evaluation(self):
        """
        Evaluates the performance of the network on a given minibatch.
        """
        logits_series = self.output_layer()
        with tf.variable_scope(constants.PERFORMANCE):
            row_lengths_series = tf.unstack(self.batch_sizes, name="unstack_batch_sizes")
            labels_series = tf.unstack(self.batch_y_placeholder, axis=1, name="unstack_labels_series")
            self.accuracy = calculate_accuracy(labels_series, self.predictions_series)
            self.total_loss_op = calculate_loss(logits_series, labels_series, row_lengths_series)
        return self.total_loss_op
    # End of performance_evaluation()

    def output_layer(self):
        """
        Creates the tensorflow variables and operations needed to compute the network outputs.
        """
        states_series = self.hidden_layer()
        with tf.variable_scope(constants.OUTPUT):
            states_series = tf.unstack(states_series, axis=1, name="unstack_states_series")
            self.batch_y_placeholder = tf.placeholder(
                dtype=tf.float32,
                shape=np.shape(self.batch_x_placeholder),
                name="output_placeholder")
            self.out_weights = tf.Variable(
                initial_value=np.random.rand(self.settings.rnn.hidden_size, self.dataset.vocabulary_size),
                dtype=tf.float32,
                name="out_weights")
            self.out_bias = tf.Variable(
                np.zeros((self.dataset.vocabulary_size)),
                dtype=tf.float32,
                name="out_bias")
            logits_series = [
                tf.nn.xw_plus_b(state, self.out_weights, self.out_bias, name="state_times_out_weights")
                for state in states_series] #Broadcasted addition
        with tf.variable_scope("predictions"):
            self.predictions_series = [tf.nn.softmax(logits) for logits in logits_series]
        return logits_series
    # End of output_layer()

    def hidden_layer(self):
        """
        Creates the tensorflow variables and operations needed to compute the hidden layer state.
        """
        inputs_series = self.input_layer()
        with tf.variable_scope(constants.HIDDEN):
            self.batch_sizes = tf.placeholder(
                dtype=tf.int32,
                shape=[self.settings.train.batch_size],
                name="batch_sizes")
            hidden_state, self.hidden_state_placeholder, self.hidden_state_shape = layered_state_tuple(
                self.settings.rnn.layers, self.settings.train.batch_size, self.settings.rnn.hidden_size)
            cell = rnn_cell(self.settings.rnn.layers, self.settings.rnn.hidden_size, self.settings.rnn.dropout)
            states_series, self.current_state = tf.nn.dynamic_rnn(
                cell=cell,
                inputs=inputs_series,
                initial_state=hidden_state,
                sequence_length=self.batch_sizes)
        return states_series
    # End of hidden_layer()

    def input_layer(self):
        """
        Creates the tensorflow variables and operations needed to perform the embedding lookup.
        """
        with tf.variable_scope(constants.INPUT):
            self.batch_x_placeholder = tf.placeholder(
                dtype=tf.int32,
                shape=[self.settings.train.batch_size, self.settings.train.truncate],
                name="input_placeholder")
            if self.dataset.data_type == constants.TYPE_CHOICES[0]: # data type = 'text'
                inputs_series = token_to_vector(self.dataset.vocabulary_size, self.settings.rnn.hidden_size,
                    self.batch_x_placeholder)
            else:
                print("ERROR: Numeric inputs cannot be handled yet.")
                exit(-1)
        return inputs_series
    # End of input_layer()

    def init_saver(self):
        """
        Creates the variables needed to save the model weights and tensorboard summaries.
        """
        self.run_dir = saver.load_meta(self.model_path)
        self.summary_writer, self.summary_ops = tensorboard.init_tensorboard(self)
        self.variables = ray.experimental.TensorFlowVariables(self.total_loss_op, self.session)
    # End of init_saver()
