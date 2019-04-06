import tensorflow as tf
import numpy as np
import random
import pickle
from models import utils, GCN
from sklearn.metrics import accuracy_score
import scipy.sparse as sp
import networkx as nx
import matplotlib.pyplot as plt


if __name__ == "__main__":
    flags = tf.app.flags
    FLAGS = flags.FLAGS
    flags.DEFINE_string('dataset', 'citeseer', 'Dataset string.')  # 'cora', 'citeseer', 'pubmed'
    flags.DEFINE_float('learning_rate', 0.01, 'Initial learning rate.')
    flags.DEFINE_integer('epochs', 200, 'Number of epochs to train.')
    flags.DEFINE_string('model', 'gcn', 'Model string.')  # 'gcn', 'gcn_cheby', 'dense'
    flags.DEFINE_integer('hidden1', 32, 'Number of units in hidden layer 1.')
    flags.DEFINE_integer('hidden2', 16, 'Number of units in hidden layer 2.')
    flags.DEFINE_float('dropout', 0.2, 'Dropout rate (1 - keep probability).')
    flags.DEFINE_float('weight_decay', 5e-4, 'Weight for L2 loss on embedding matrix.')
    flags.DEFINE_integer('early_stopping', 2, 'Tolerance for early stopping (# of epochs).')
    flags.DEFINE_float('train_share', 0.1, 'Percent of testing size.')
    flags.DEFINE_bool('output', False, 'Toggle the output.')
    flags.DEFINE_bool('verbose', False, 'Toogle the verbose.')

    seed = 15
    np.random.seed(seed)
    tf.set_random_seed(seed)

    # Load network, basic setup
    _A_obs, _X_obs, _z_obs = utils.load_npz('data/{}.npz'.format(FLAGS.dataset))
    _A_obs = _A_obs + _A_obs.T

    # select the largest connected component
    lcc = utils.largest_connected_components(_A_obs)

    # update based on lcc
    _A_obs = _A_obs[lcc][:, lcc]
    _X_obs = _X_obs[lcc].astype('float32')
    _z_obs = _z_obs[lcc]

    _N = _A_obs.shape[0]
    _K = _z_obs.max() + 1
    _Z_obs = np.eye(_K)[_z_obs]
    _An = utils.preprocess_graph(_A_obs)
    sizes = [16, _K]
    degrees = _A_obs.sum(0).A1.astype('int32')

    train_share = FLAGS.train_share
    val_share = 0.1
    unlabeled_share = 1 - val_share - train_share
    train_size = int(_N * train_share)
    val_size = int(_N * val_share)
    unlabeled_size = _N - train_size - val_size

    split_train, split_val, split_unlabeled = utils.train_val_test_split_tabular(np.arange(_N),
                                                train_size=train_size,
                                                val_size=val_size,
                                                test_size=unlabeled_size,
                                                stratify=_z_obs)

    model = GCN.GCN(sizes, _An, _X_obs)

    # build feed_dict
    def build_feed_dict(model, node_ids, labels_logits):
        return {model.node_ids: node_ids, 
                model.node_labels: labels_logits[node_ids]}

    feed_train = build_feed_dict(model, split_train, _Z_obs)
    feed_val = build_feed_dict(model, split_val, _Z_obs)
    feed_unlabeled = build_feed_dict(model, split_unlabeled, _Z_obs)
    
    iters = []
    train_losses = []
    train_accs = []
    val_losses = []
    val_accs = []
    test_losses = []
    test_accs = []
    best = 100
    treshold = 2
    early_stopping = treshold
    model.train_model(split_train, split_val, _Z_obs)
    test_loss, test_acc = model.eval_model(split_unlabeled, _Z_obs)

    print(
        "dataset: {}".format(FLAGS.dataset),
        "train_share: {:.1f}".format(FLAGS.train_share),
        "test_loss: {:.3f}".format(test_loss), 
        "test_acc: {:.3f}".format(test_acc)
    )