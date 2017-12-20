from __future__ import print_function

import numpy as np
import torch
import torch.nn as nn
from torch.autograd import Variable


def orthogonal(shape):
	flat_shape = (shape[0], np.prod(shape[1:]))
    a = np.random.normal(0.0, 1.0, flat_shape)
    u, _, v = np.linalg.svd(a, full_matrices=False)
    q = u if u.shape == flat_shape else v
    return torch.Tensor(q.reshape(shape))

def orthogonal_initializer(shape, scale=1.0, dtype=torch.FloatTensor):
    return torch.Tensor(orthogonal(shape) * scale).type(dtype)
    

def layer_norm_all(h, base, num_units):
    # Layer Norm (faster version)
    #
    # Performs layer norm on multiple base at once (ie, i, g, j, o for lstm)
    #
    # Reshapes h in to perform layer norm in parallel
    """
    with tf.variable_scope(scope):
        h_reshape = tf.reshape(h, [-1, base, num_units])
        mean = tf.reduce_mean(h_reshape, [2], keep_dims=True)
        var = tf.reduce_mean(tf.square(h_reshape - mean), [2], keep_dims=True)
        epsilon = tf.constant(1e-3)
        rstd = tf.rsqrt(var + epsilon)
        h_reshape = (h_reshape - mean) * rstd
        # reshape back to original
        h = tf.reshape(h_reshape, [-1, base * num_units])

        alpha = tf.get_variable('layer_norm_alpha', [4 * num_units],
                                initializer=tf.constant_initializer(1.0), dtype=tf.float32)
        bias = tf.get_variable('layer_norm_bias', [4 * num_units],
                               initializer=tf.constant_initializer(0.0), dtype=tf.float32)

    return (h * alpha) + bias
	"""
    
    h_reshape = h_reshape.view([-1, base, num_units])
    mean = h_reshape.mean(dim = 2)
    temp = (h_reshape - mean)**2
    var = temp.mean(dim = 2)

    epsilon = nn.init.constant(1e-3)
    dtype = torch.FloatTensor
    
    h = h_reshape.view([-1, base * num_units])

    alpha = Variable(torch.ones(4*num_units).type(dtype), requires_grad=True)

    bias = Variable(torch.ones(4*num_units).type(dtype), requires_grad=True)

    return (h*alpha) + bias



def moments_for_layer_norm(x, axes=1, name=None):
    # output for mean and variance should be [batch_size]
    # from https://github.com/LeavesBreathe/tensorflow_with_latest_papers
    epsilon = 1e-3  # found this works best.
    if not isinstance(axes, int): axes = axes[0]

    mean = x.mean(dim = axes)

    variance = (((x-mean)**2).mean(dim = axes) + epsilon)**0.5

    return mean, variance

    #mean = tf.reduce_mean(x, axes, keep_dims=True)
    #variance = tf.sqrt(tf.reduce_mean(tf.square(x - mean), axes, keep_dims=True) + epsilon)
    #return mean, variance


def layer_norm(x, alpha_start=1.0, bias_start=0.0):
    # derived from:
    # https://github.com/LeavesBreathe/tensorflow_with_latest_papers, but simplified.
    with tf.variable_scope(scope):
        num_units = int(x.size()[1])

        #alpha = tf.get_variable('alpha', [num_units],
        #                        initializer=tf.constant_initializer(alpha_start), dtype=tf.float32)
        #bias = tf.get_variable('bias', [num_units],
        #                       initializer=tf.constant_initializer(bias_start), dtype=tf.float32)

        alpha = Variable(torch.ones(4*num_units).type(dtype), requires_grad=True)

	    bias = Variable(torch.ones(4*num_units).type(dtype), requires_grad=True)

        mean, variance = moments_for_layer_norm(x)
        y = (alpha * (x - mean)) / (variance) + bias
    return y

def zoneout(new_h, new_c, h, c, h_keep, c_keep, is_training):
	mask_c = torch.ones_like(c)
	mask_h = torch.ones_like(h)

	c_dropout = nn.Dropout(p = 1-c_keep)
	h_dropout = nn.Dropout(p= 1-h_keep)

	if is_training:
		mask_c = c_dropout(mask_c)
		mask_h = h_dropout(mask_h)

	mask_c *= c_keep
	mask_h *= h_keep

	h = new_h * mask_h + (-mask_h + 1.) * h
	c = new_c * mask_c + (-mask_c + 1.) * c

	return h, c