
# This is used to train the model

# Written by 
# 	Luca Naterop
# 	Sandro Giacomuzzi
# as part of a semester project (AI music composition)
# at ETH Zuerich, 2017

# refer to README.md for usage

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from Util import create_batches
from Util import meanOfMaxProb
from Util import meanByProb
from Util import distByProb
from Util import printAsCSV
import numpy as np
import tensorflow as tf
from batchloader import BatchLoader
from tabulate import tabulate
import sys
import os

# Parse command line arguments
csvfile = sys.argv[1]

if '-folder' in sys.argv:
	loadCheckpoint = True
	index = sys.argv.index('-folder')
	folder_name = sys.argv[index+1]
	print('folder name: ' + folder_name)

if '-checkpoint' in sys.argv:
	loadCheckpoint = True
	index = sys.argv.index('-checkpoint')
	checkpoint_path = sys.argv[index+1]
else:
	loadCheckpoint = False

# Make sure that folder structure exists
if not os.path.exists(folder_name):
    os.makedirs(folder_name)
if not os.path.exists(folder_name+'/checkpoints'):
    os.makedirs(folder_name+'/checkpoints')
if not os.path.exists(folder_name+'/generated'):
    os.makedirs(folder_name+'/generated')

# Reading data
print('reading data..')
data = np.genfromtxt(csvfile, delimiter=',')
data_max = np.max(data)
data = data/data_max

# Parameters
N = data.shape[0]		# data set size
L = data.shape[1]		# amount of standard outputs if there was no mdn
hidden_units = 32		# amount of hidden units
hidden_layers = 2		# amount of hidden layers
K = 7 					# amount of mixtures
max_time = 50			# max time
B_hat = N-max_time-1 	# total amount of batches
B = 100  				# amount of batches to pass in one
epochs = 1000		
noise = 0.01
learning_rate = 0.01
sample_size = 200	
sample_every = 2		# sample every ?? epochs
save_every = 2			# save model every ?? epochs

print('--------------------------------- PARAMETERS ---------------------------------')
print('N = ' + str(N) + ', L = ' + str(L) + ', K = ' + str(K) + 
	', B = ' + str(B) + ', hidden_units = ' + str(hidden_units) + 
	', hidden_layers = ' + str(hidden_layers) + ', lr = ' + str(learning_rate))
print('------------------------------------------------------------------------------')

# plt.imshow(np.transpose(data), cmap='hot', interpolation='nearest')
# plt.show()

# model
print('creating the model...')
outputs = (L+2)*K

x = tf.placeholder(dtype=tf.float64, shape=[None,None,L])				# (B,T,L)
y = tf.placeholder(dtype=tf.float64, shape=[None,L])					# (B,L)

B_ = tf.shape(x)[0]
T = tf.shape(x)[1]

# init_state = tf.placeholder(tf.float64, [hidden_layers, 2, None, hidden_units])
# l = tf.unstack(init_state, axis=0)
# rnn_tuple_state = tuple( [tf.contrib.rnn.LSTMStateTuple(l[idx][0], l[idx][1]) for idx in range(hidden_layers)])

cell = tf.contrib.rnn.LSTMCell(hidden_units, use_peepholes=False)
cell = tf.contrib.rnn.DropoutWrapper(cell, input_keep_prob=0.7)
cell = tf.contrib.rnn.MultiRNNCell([cell] * hidden_layers)
output, state = tf.nn.dynamic_rnn(cell,x, dtype=tf.float64)				# output: (B,T,H), state: ([B,H],[B,H])
output = tf.transpose(output, [1,0,2])									# (T,B,H)
last = tf.gather(output, T-1)											# (B,H)

W_out = tf.Variable(tf.random_normal([hidden_units,outputs], stddev=0.001, dtype=tf.float64))
b_out = tf.Variable(tf.random_normal([outputs], stddev=0.001, dtype=tf.float64))
y_out = tf.matmul(last,W_out) + b_out									# (B,(L+2)K)

def getMixtureCoefficients(output):
	pi_k, sigma_k, mu_k = tf.split(output, [K,K,L*K], 1)									# 
	mu_k = tf.reshape(mu_k, [B_,K,L])														# (B,K,L)
	pi_k = tf.nn.softmax(pi_k)																# (B,K)
	sigma_k = tf.exp(sigma_k) 																# (B,K)
	return pi_k, sigma_k, mu_k
pi_k, sigma_k, mu_k = getMixtureCoefficients(y_out)											# (B,K)

def gaussian(y, mu_k, sigma_k):
	y = tf.reshape(y, [B_,1,L])
	norm = tf.reduce_sum(tf.square(y-mu_k),axis=2)	# sums over the L dimensions -> we get shape (B,K) again
	phi_k = -tf.div(norm, 2*tf.square(sigma_k))		
	phi_k = tf.exp(phi_k)
	phi_k = tf.divide(phi_k, sigma_k)
	return phi_k

phi_k = gaussian(y, mu_k, sigma_k)
loss = tf.multiply(phi_k,pi_k)
loss = tf.reduce_sum(loss, 1, keep_dims=True)
loss = tf.reduce_sum(-tf.log(loss))

# other branch of graph for predictions
max_indices = tf.argmax(tf.div(pi_k, sigma_k), 1)

train_op = tf.train.AdamOptimizer(learning_rate).minimize(loss)

# sample
def sample(Seed, amount):
	seed = np.copy(Seed)
	B = 1
	"synthesizes from the model"
	print('sampling from the model....')
	S = seed.shape[0]
	L = seed.shape[1]
	samples = np.zeros([S+amount, L])
	samples[0:S,:] = seed
	# State = np.zeros([hidden_layers,2,1,hidden_units])

	for i in range(0,amount):
		mu_i, maxima, pi_i, sigma_i, State = sess.run([mu_k, max_indices, pi_k, sigma_k, state], {x: np.expand_dims(seed, axis=0)})
		maxima 	= np.array(maxima)
		mu_i 	= np.array(mu_i)
		pi_i 	= np.array(pi_i)
		sigma_i = np.array(sigma_i)
		predictions = meanByProb(mu_i,pi_i,sigma_i)
		# seed = predictions
		seed[0:-1,:] = seed[1:,:]
		seed[-1,:] = predictions
		samples[S+i,:] = predictions
	samples = samples
	return samples

# launch session, load checkpoint or initialize variables?

sess = tf.Session()
saver = tf.train.Saver(max_to_keep=1)
if loadCheckpoint:
	print('loading model from checkpoint')
	saver.restore(sess, checkpoint_path)
else:
	print('initializing a new model (no checkpoint was given)')
	sess.run(tf.global_variables_initializer())

# training
print('starting training...')
all_inputs, all_targets = create_batches(data, max_time)
B_hat = all_inputs.shape[0]
# State = np.zeros([hidden_layers,2,B_,hidden_units])
smoothloss = 100
for epoch in range(epochs):
	for i in range(0,int(B_hat/B)):
		inputs = all_inputs[i:i+B,:,:]
		inputs = inputs + np.random.rand(inputs.shape[0], inputs.shape[1],inputs.shape[2])*noise
		targets = all_targets[i:i+B,:]
		_, cost,State = sess.run([train_op, loss, state],{x: inputs, y: targets})
		cost = cost/B
		smoothloss = 0.99*smoothloss + 0.01*cost
		print('epoch = ' + str(epoch) + ', i = ' + str(i) + ' , loss = ' + str(cost))
	
	if epoch%sample_every == 0:
		# sample from the model
		seedstart = int(np.floor(np.random.rand()*N))
		seed = data[seedstart:seedstart+max_time,:]
		samples = sample(seed, sample_size)
		samples = samples*data_max
		# print(np.round(samples, decimals=1))
		np.savetxt(folder_name + '/generated/l=' + str(cost) + '.csv', np.round(samples, decimals=3), delimiter=',')

	if epoch%save_every == 0:
		# save the model
		save_path = saver.save(sess, folder_name+'/checkpoints/E'+format(epoch,'04')+'L'+str(round(cost,3)))
		print("Model saved in file: %s" % save_path)

# plt.imshow(np.transpose(samples), cmap='hot', interpolation='nearest')
# plt.show()
sess.close()
