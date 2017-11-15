import tensorflow as tf
import numpy as np
import os
import gzip
import pickle as cPickle
import matplotlib.pyplot as plt


#Load MNIST
def mnist(datasets_dir='./data'):
    if not os.path.exists(datasets_dir):
        os.mkdir(datasets_dir)
    data_file = os.path.join(datasets_dir, 'mnist.pkl.gz')
    if not os.path.exists(data_file):
        print('... downloading MNIST from the web')
        try:
            import urllib
            urllib.urlretrieve('http://google.com')
        except AttributeError:
            import urllib.request as urllib
        url = 'http://www.iro.umontreal.ca/~lisa/deep/data/mnist/mnist.pkl.gz'
        urllib.urlretrieve(url, data_file)

    print('... loading data')
    # Load the dataset
    f = gzip.open(data_file, 'rb')
    try:
        train_set, valid_set, test_set = cPickle.load(f, encoding="latin1")
    except TypeError:
        train_set, valid_set, test_set = cPickle.load(f)
        f.close()

    test_x, test_y = test_set
    test_x = test_x.astype('float32')
    test_x = test_x.astype('float32').reshape(test_x.shape[0], 1, 28, 28)
    test_y = test_y.astype('int32')
    valid_x, valid_y = valid_set
    valid_x = valid_x.astype('float32')
    valid_x = valid_x.astype('float32').reshape(valid_x.shape[0], 1, 28, 28)
    valid_y = valid_y.astype('int32')
    train_x, train_y = train_set
    train_x = train_x.astype('float32').reshape(train_x.shape[0], 1, 28, 28)
    train_y = train_y.astype('int32')
    rval = [(train_x, train_y), (valid_x, valid_y), (test_x, test_y)]
    print('... done loading data')
    return rval

# load
Dtrain, Dval, Dtest = mnist()
X_train, y_train = Dtrain
X_valid, y_valid = Dval

n_train_samples = X_train.shape[0]
train_idxs = np.random.permutation(X_train.shape[0])[:n_train_samples]
X_train = X_train[train_idxs]
y_train = y_train[train_idxs]

def cnn_model_fn(features, labels, mode, params):
    """Model function for CNN."""
    num_filters = params["num_filters"]
    learning_rate = params["learning_rate"]

    # Input Layer
    input_layer = tf.reshape(features["x"], [-1, 28, 28, 1])

    # Convolutional Layer #1
    conv1 = tf.layers.conv2d(
        inputs=input_layer,
        filters=num_filters,
        kernel_size=[3, 3],
        padding="same",
        activation=tf.nn.relu)

    # Pooling Layer #1
    pool1 = tf.layers.max_pooling2d(inputs=conv1, pool_size=[2, 2], strides=1)

    # Convolutional Layer #2 and Pooling Layer #2
    conv2 = tf.layers.conv2d(
        inputs=pool1,
        filters=num_filters,
        kernel_size=[3, 3],
        padding="same",
        activation=tf.nn.relu)
    pool2 = tf.layers.max_pooling2d(inputs=conv2, pool_size=[2, 2], strides=1)

    # Dense Layer
    pool2_flat = tf.reshape(pool2, [-1, 26 * 26 * num_filters])
    dense = tf.layers.dense(inputs=pool2_flat, units=128, activation=tf.nn.relu)
    dropout = tf.layers.dropout(
        inputs=dense, rate=0.4, training=mode == tf.estimator.ModeKeys.TRAIN)

    # Logits Layer
    logits = tf.layers.dense(inputs=dropout, units=10)

    predictions = {
        # Generate predictions (for PREDICT and EVAL mode)
        "classes": tf.argmax(input=logits, axis=1),
        # Add `softmax_tensor` to the graph. It is used for PREDICT and by the
        # `logging_hook`.
        "probabilities": tf.nn.softmax(logits, name="softmax_tensor")
    }

    if mode == tf.estimator.ModeKeys.PREDICT:
        return tf.estimator.EstimatorSpec(mode=mode, predictions=predictions)

    #Calculate Loss (for both TRAIN and EVAL modes)
    onehot_labels = tf.one_hot(indices=tf.cast(labels, tf.int32), depth=10)
    loss = tf.losses.softmax_cross_entropy(
        onehot_labels=onehot_labels, logits=logits)

    # Configure the Training Op (for TRAIN mode)
    if mode == tf.estimator.ModeKeys.TRAIN:
        optimizer = tf.train.GradientDescentOptimizer(learning_rate=learning_rate)
        train_op = optimizer.minimize(
            loss=loss,
            global_step=tf.train.get_global_step())
        return tf.estimator.EstimatorSpec(mode=mode, loss=loss, train_op=train_op)

    # Add evaluation metrics (for EVAL mode)
    eval_metric_ops = {
        "accuracy": tf.metrics.accuracy(
            labels=labels, predictions=predictions["classes"])}
    return tf.estimator.EstimatorSpec(
            mode=mode, loss=loss, eval_metric_ops=eval_metric_ops)

# #learning rates with gpu
rates = [0.1, 0.01, 0.001, 0.0001]
max_epochs = 100
axis = np.arange(max_epochs)
plt.figure()
color = ['r', 'g', 'b', 'o']
for rate, c in zip(rates, color):
    # Create the Estimator
    mnist_cnn = tf.estimator.Estimator(model_fn=cnn_model_fn, model_dir="/tmp/mnist_convnet_model_lr"+str(i), params ={"num_filters": 16, "learning_rate": rate})
    losses = np.zeros(max_epochs)

    for i in range(max_epochs):
        # Train the model
        train_input_fn = tf.estimator.inputs.numpy_input_fn(
                x={"x": X_train},
                y=y_train,
                batch_size=64,
                num_epochs=None,
                shuffle=True)
        mnist_cnn.train(
                input_fn=train_input_fn,
                steps=1)

        eval_input_fn = tf.estimator.inputs.numpy_input_fn(
            x={"x": X_valid},
            y=y_valid,
            num_epochs=1,
            shuffle=False)
        losses[i] = mnist_cnn.evaluate(input_fn=eval_input_fn)["loss"]
        print("Validation loss in epoch {}: {}" .format(i, losses[i]))

    print("Learning rate: {}." .format(rate))
    plt.plot(axis, losses, c=c)
plt.show()


#training speed with GPU and CPU on different filter sizes
import time

nums = [8, 16, 32, 64, 128, 256]
times = [0, 0, 0, 0, 0, 0]

for i in range(len(nums)):
    # Create the Estimator
    mnist_cnn = tf.estimator.Estimator(model_fn=cnn_model_fn, model_dir="/tmp/mnist_convnet_model_time_gpu" + str(i), params ={"num_filters": nums[i], "learning_rate": 0.1})
    start_gpu= time.time()
    max_epochs = 100

    for i in range(max_epochs):
        # Train the model
        train_input_fn = tf.estimator.inputs.numpy_input_fn(
                x={"x": X_train},
                y=y_train,
                batch_size=64,
                num_epochs=None,
                shuffle=True)
        mnist_cnn.train(
                input_fn=train_input_fn,
                steps=1)

        eval_input_fn = tf.estimator.inputs.numpy_input_fn(
            x={"x": X_valid},
            y=y_valid,
            num_epochs=1,
            shuffle=False)
        val_loss = mnist_cnn.evaluate(input_fn=eval_input_fn)
        print("Validation loss in epoch {}: {%.2f}" .format(val_loss["global_step"], val_loss["loss"]))
        print("Accuracy on validation set in epoch {}: {%.2f}" .format(val_loss["global_step"], val_loss["accuracy"]))
        
    end_gpu = time.time()
    diff = end_gpu - start_gpu
    times[i] = diff
    print("{} filters with GPU. Time was: {} ms" .format(nums[i], diff))

plt.figure()
plt.scatter(nums, times, c='g')

#with cpu
with tf.device('/cpu:0'):
    nums = [8, 16, 32, 64]
    times = [0, 0, 0, 0]

    for i in range(len(nums)):
        # Create the Estimator
        mnist_cnn = tf.estimator.Estimator(model_fn=cnn_model_fn, model_dir="/tmp/mnist_convnet_model_time_cpu" + str(i), params ={"num_filters": nums[i], "learning_rate": 0.1})
        start_gpu= time.time()
        max_epochs = 100

        for j in range(max_epochs):
            train_input_fn = tf.estimator.inputs.numpy_input_fn(
                x={"x": X_train},
                y=y_train,
                batch_size=64,
                num_epochs=None,
                shuffle=True)
            mnist_cnn.train(
                input_fn=train_input_fn,
                steps=1)

            eval_input_fn = tf.estimator.inputs.numpy_input_fn(
                x={"x": X_valid},
                y=y_valid,
                num_epochs=1,
                shuffle=False)
            val_loss = mnist_cnn.evaluate(input_fn=eval_input_fn)
            print("Validation loss in epoch {}: {%.2f}" .format(val_loss["global_step"], val_loss["loss"]))
            print("Accuracy on validation set in epoch {}: {%.2f}" .format(val_loss["global_step"], val_loss["accuracy"]))

        end_gpu = time.time()
        diff = end_gpu -start_gpu
        times[i] = diff
        print("{} filters with CPU. Time was: {%.2f} ms" .format(nums[i], diff))

print(nums)
print(times)
plt.scatter(nums, times, c='r')
plt.show()

if __name__ =="__main__":
   #with gpu
   #with tf.device("/device:GPU:0"):
    #    tf.app.run()
    tf.app.run()
